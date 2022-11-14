import pandas as pd

from typing import Union, List

from github.Repository import Repository
from tqdm import tqdm

from securityaware.data.dataset import ChainMetadata
from securityaware.handlers.plugin import PluginHandler
from securityaware.utils.misc import split_github_commits, clean_github_commits, project_from_chain, \
    parse_published_date, transform_to_commits


class NVDPrepare(PluginHandler):
    """
        NVDPrepare plugin
    """

    class Meta:
        label = "nvd_prepare"

    def run(self, dataset: pd.DataFrame, tokens: Union[str, list] = None, metadata: bool = True,
            **kwargs) -> Union[pd.DataFrame, None]:
        """
            runs the plugin
        """
        metadata_path = self.path / f'{self.output.stem}_metadata.csv'
        self.set('metadata_path', metadata_path)
        df_normalized_path = self.path / f'{self.output.stem}_normalized.csv'
        self.set('normalized_path', df_normalized_path)
        self.github_handler.tokens = tokens

        if not df_normalized_path.exists():
            dataset.rename(inplace=True, columns={'cve_id': 'vuln_id', 'cwes': 'cwe_id', 'commits': 'chain',
                                                  'description': 'summary', 'impact': 'score'})
            dataset = dataset[['vuln_id', 'cwe_id', 'score', 'chain', 'summary', 'published_date']]
            dataset = self.normalize(dataset)

            for idx, row in tqdm(dataset.iterrows()):
                self.multi_task_handler.add(chain=row['chain']).update_id(idx)

            self.multi_task_handler(func=self.github_handler.normalize_sha)
            df_normalized_sha = self.multi_task_handler.get_tasks(as_frame=True)
            df_normalized_sha = df_normalized_sha[['result']].rename(columns={'result': 'chain'})

            dataset.drop(columns=['chain'], inplace=True)
            dataset = pd.merge(dataset, df_normalized_sha, left_index=True, right_index=True)
            dataset = dataset.dropna(subset=['chain'])
            self.app.log.info(f"Entries (after nan drop): {len(dataset)}")

            dataset = transform_to_commits(dataset)
            dataset.to_csv(str(df_normalized_path))
        else:
            dataset = pd.read_csv(str(df_normalized_path))

        self.app.log.info(f"Size after normalization: {len(dataset)}")

        if metadata:
            if not metadata_path.exists():
                del self.multi_task_handler
                for project, rows in tqdm(dataset.groupby(['project'])):
                    self.multi_task_handler.add(project=project, chains=rows['chain'].to_list(),
                                                commits=rows['commit_sha'].to_list(), indexes=rows.index)

                self.multi_task_handler(func=self.github_handler.get_project_metadata)
                metadata_df = pd.concat(self.multi_task_handler.results())
                metadata_df.to_csv(str(metadata_path))
            else:
                metadata_df = pd.read_csv(str(metadata_path))

            dataset.drop(columns=['commit_sha'], inplace=True)
            dataset = pd.merge(dataset, metadata_df, left_index=True, right_index=True)

            self.app.log.info(f"Size after merging with metadata: {len(dataset)}")

        return dataset

    def normalize(self, df: pd.DataFrame):
        self.app.log.info("Normalizing NVD ...")
        df['chain'] = df['chain'].apply(lambda x: split_github_commits(x))
        self.app.log.info(f"Size after split {len(df)}")

        df['chain'] = df['chain'].apply(lambda x: clean_github_commits(x))
        self.app.log.info(f"Entries after clean {len(df)}")

        df = df.dropna(subset=['chain'])
        self.app.log.info(f"Entries (After duplicates): {len(df)}")

        df['chain_len'] = df['chain'].apply(lambda x: len(x))
        df['project'] = df['chain'].apply(lambda x: project_from_chain(x))
        df['published_date'] = df['published_date'].apply(lambda x: parse_published_date(x))

        return df


def load(app):
    app.handler.register(NVDPrepare)
