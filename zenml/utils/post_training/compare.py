from typing import List

import pandas as pd
import panel as pn
import param
import plotly.express as px
import plotly.graph_objects as go
import tensorflow_model_analysis as tfma

from zenml.enums import PipelineStatusTypes, GDPComponent
from zenml.pipelines import TrainingPipeline
from zenml.repo import Repository

pn.extension('plotly')


def parse_metrics(d):
    tmp = d.copy()
    for x in d:
        if x.startswith('metric_'):
            m = tmp.pop(x)
            for k, v in m.items():
                tmp[x + '_' + k] = v['doubleValue']
    return tmp


class Application(param.Parameterized):
    pipeline_run_selector = param.ListSelector(default=[], objects=[])
    hyperparameter_selector = param.ListSelector(default=[], objects=[])

    slicing_metric_selector = param.ObjectSelector(default='', objects=[''])
    performance_metric_selector = param.ObjectSelector(objects=[])

    def __init__(self, datasource=None, **params):
        super(Application, self).__init__(**params)

        # lists
        result_list = []
        hparam_list = []
        repo: Repository = Repository.get_instance()
        self.datasource = datasource

        # get all pipelines in this workspace
        if datasource:
            # filter pipeline by datasource, and then the training ones
            all_pipelines: List[TrainingPipeline] = \
                repo.get_pipelines_by_datasource(datasource)
            all_pipelines = [p for p in all_pipelines if
                             p.PIPELINE_TYPE == TrainingPipeline.PIPELINE_TYPE]
        else:
            all_pipelines: List[TrainingPipeline] = repo.get_pipelines_by_type(
                [
                    TrainingPipeline.PIPELINE_TYPE])

        # get a dataframe of all results + all hyperparameter combinations
        for p in all_pipelines:
            # This is slowing the comparison down but
            # necessary to update the status of each run
            if p.get_status() == PipelineStatusTypes.Succeeded.name:
                eval_path = p.get_artifacts_uri_by_component(
                    GDPComponent.Evaluator.name)[0]

                evaluation = tfma.load_eval_result(eval_path)
                for s, m in evaluation.slicing_metrics:
                    result_list.append(dict([(
                        'pipeline_name', '{}'.format(p.name)),
                        ('slice_name', s[0][0] if s else ''),
                        ('slice_value', s[0][1] if s else '')]))
                    result_list[-1].update({f'metric_{k}': m[k]['']
                                            for k, v in m.items()})

                h_dict = p.get_hyperparameters()
                h_dict['pipeline_name'] = p.name
                hparam_list.append(h_dict)

        self.results = pd.DataFrame([parse_metrics(r) for r in
                                     result_list])
        self.hparam_info = pd.DataFrame(hparam_list)

        # set params
        self.param.pipeline_run_selector.objects = self.results[
            'pipeline_name'].unique()

    @param.depends('pipeline_run_selector', watch=True)
    def _updated_context(self):
        df = self.results[self.results['pipeline_name'].isin(
            self.pipeline_run_selector)]
        df = df.dropna(axis=1, how='all')

        slicing_metric_list = sorted(list(df['slice_name'].unique()))

        performance_metric_set = {c for c in df.columns if
                                  c.startswith('metric_')}
        performance_metric_list = [None] + sorted(list(
            performance_metric_set))

        self.param['slicing_metric_selector'].objects = slicing_metric_list
        self.param[
            'performance_metric_selector'].objects = performance_metric_list

        # get params
        parameter_list = self.hparam_info[self.hparam_info[
            'pipeline_name'].isin(self.pipeline_run_selector)].columns
        parameter_list = [x for x in parameter_list if x !=
                          'pipeline_name']
        self.param['hyperparameter_selector'].objects = parameter_list

        self.slicing_metric_selector = ''
        self.performance_metric_selector = None

    @param.depends('slicing_metric_selector',
                   'performance_metric_selector', watch=True)
    def performance_graph(self):
        if self.performance_metric_selector:
            df = self.results[(self.results['pipeline_name'].isin(
                self.pipeline_run_selector)) &
                              (self.results['slice_name'] ==
                               self.slicing_metric_selector)]
            fig = px.scatter(df,
                             x='pipeline_name',
                             y=self.performance_metric_selector,
                             color='slice_value',
                             width=1100,
                             title='Pipeline Comparison')

            fig = fig.update_traces(mode='lines+markers')

        else:
            fig = px.scatter(pd.DataFrame(),
                             marginal_y='rug',
                             width=1100,
                             title='Pipeline Comparison')

        return fig

    @param.depends('performance_metric_selector',
                   'hyperparameter_selector', watch=True)
    def parameter_graph(self):
        if self.performance_metric_selector and len(
                self.hyperparameter_selector) > 0:
            df = self.results[(self.results['pipeline_name'].isin(
                self.pipeline_run_selector)) &
                              (self.results['slice_name'] == '')]

            # merge
            extra_df = pd.merge(self.hparam_info, df,
                                on='pipeline_name', how='left')

            dimensions = ['pipeline_name'] + self.hyperparameter_selector + \
                         [self.performance_metric_selector]

            new_dims = []
            for d in dimensions:
                try:
                    new_dims.append({'label': d, 'values':
                        pd.to_numeric(extra_df[d])})
                except:
                    u = sorted(list(extra_df[d].apply(lambda x: str(
                        x)).unique()))
                    mapping = {v: i for i, v in enumerate(u)}
                    new_dims.append({'label': d,
                                     'tickvals': [mapping[x] for x
                                                  in u],
                                     'ticktext': u,
                                     'values': extra_df[d].apply(
                                         lambda x: str(x)).map(mapping)})

            final_col = pd.to_numeric(extra_df[
                                          self.performance_metric_selector])
            fig = go.Figure(data=go.Parcoords(line=dict(
                color=final_col,
                colorscale=
                'inferno',
                showscale=True,
                cmin=min(
                    final_col),
                cmax=max(
                    final_col)),
                dimensions=new_dims))
        else:
            fig = px.scatter(pd.DataFrame(),
                             marginal_y='rug',
                             width=1100,
                             title='Hyperparameter Comparison')

        return fig


def generate_interface(datasource=None):
    app = Application(datasource=datasource)
    handlers = pn.Param(app.param)

    # Analysis Page
    analysis_page = pn.GridSpec(height=850, width=1850, max_height
    =850, max_width=1850)
    analysis_page[0:8, 0:2] = handlers[1]
    analysis_page[0:10, 8:10] = handlers[2]
    analysis_page[8:9, 0:2] = handlers[3]
    analysis_page[9:10, 0:2] = handlers[4]
    analysis_page[0:5, 2:8] = app.performance_graph
    analysis_page[5:10, 2:8] = app.parameter_graph

    interface = pn.Tabs(
        ('Analysis Page', analysis_page),
    )
    return interface
