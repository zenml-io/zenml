#  Copyright (c) maiot GmbH 2020. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import json
import os
from textwrap import dedent

import click


# IMPORT FUNCTIONS
def parse_metrics(d):
    tmp = d.copy()
    m = tmp.pop('metrics')
    for k, v in m.items():
        tmp['metric_' + k] = v['doubleValue']
    return tmp


def get_log_dir(p_uuid, r_uuid, info):
    # TODO: how do i kow that the pipeline is in this workspace, maybe i
    #   changed the ws
    ws_id = info[info[constants.ACTIVE_USER]][constants.ACTIVE_WORKSPACE]
    d_path = os.path.join(click.get_app_dir(constants.APP_NAME),
                          'eval_trainer',
                          str(ws_id),
                          str(p_uuid),
                          str(r_uuid))

    if os.path.exists(os.path.join(d_path, 'eval_model_dir')):
        return d_path

    api = ce_api.PipelinesApi(api_client(info))
    artifact = api_call(
        api.get_pipeline_artifacts_api_v1_pipelines_pipeline_id_runs_pipeline_run_id_artifacts_component_type_get,
        pipeline_id=p_uuid,
        pipeline_run_id=r_uuid,
        component_type=GDPComponent.Trainer.name)
    download_artifact(artifact[0].to_dict(), path=d_path)
    return d_path


def get_eval_dir(p_uuid, r_uuid, info, d_path=None):
    ws_id = info[info[constants.ACTIVE_USER]][constants.ACTIVE_WORKSPACE]

    if d_path is None:
        d_path = os.path.join(click.get_app_dir(constants.APP_NAME),
                              'eval_evaluator',
                              str(ws_id),
                              str(p_uuid),
                              str(r_uuid))

    if os.path.exists(os.path.join(d_path, 'eval_config.json')):
        return d_path

    api = ce_api.PipelinesApi(api_client(info))
    artifact = api_call(
        api.get_pipeline_artifacts_api_v1_pipelines_pipeline_id_runs_pipeline_run_id_artifacts_component_type_get,
        pipeline_id=p_uuid,
        pipeline_run_id=r_uuid,
        component_type=GDPComponent.Evaluator.name)

    # TODO: [LOW] artifact[1] hard-coded because of upgrade to 0.21.4
    download_artifact(artifact[0].to_dict(), path=d_path)

    # replace google path with local path
    with open(os.path.join(d_path, 'eval_config.json'), 'r') as f:
        eval_config = json.load(f)

    # now override the google path to local path
    eval_config['modelLocations'][''] = d_path

    with open(os.path.join(d_path, 'eval_config.json'), 'w') as f:
        json.dump(eval_config, f)

    return d_path


# THE REAL STUFF
def import_block():
    block = '''\
        import param
        import panel as pn
        import pandas as pd
        import plotly.express as px
        import tensorflow_model_analysis as tfma
        import ce_api
        from ce_cli import constants
        from ce_cli.utils import api_call, api_client, download_artifact, 
        notice, \
            declare, format_uuid, find_closest_uuid
        import plotly.graph_objects as go

        from ce_cli.evaluation import parse_metrics, get_eval_dir

        pn.extension('plotly')
    '''
    return dedent(block)[:-1]


def info_block(info):
    block = '''\
        info = {}
    '''.format(info)
    return dedent(block)[:-1]


def application_block():
    block = '''\
        class Application(param.Parameterized):
            pipeline_run_selector = param.ListSelector(default=[], objects=[
            ]) # 1
            hyperparameter_selector = param.ListSelector(default=[], 
            objects=[]) # 2

            slicing_metric_selector = param.ObjectSelector(default='', 
            objects=['']) # 3
            performance_metric_selector = param.ObjectSelector(objects=[]) # 4 


            def __init__(self, **params):
                super(Application, self).__init__(**params)
                # apis
                p_api = ce_api.PipelinesApi(api_client(info))
                ws_api = ce_api.WorkspacesApi(api_client(info))

                user = info[constants.ACTIVE_USER]
                active_workspace = info[user][constants.ACTIVE_WORKSPACE]

                # lists 
                result_list = []
                hparam_list = []

                # get all pipelines in this workspace
                all_pipelines = api_call(
                ws_api.get_workspaces_pipelines_api_v1_workspaces_workspace_id_pipelines_get, 
                                         active_workspace)

                # get a dataframe of all results + all hyperparameter 
                combinations
                for p in all_pipelines:
                    if p.pipeline_runs is not None and len(p.pipeline_runs)>0:
                        for run in p.pipeline_runs:
                            # This is slowing the comparison down but 
                            necessary to update the status of each run
                            r = api_call(
                                p_api.get_pipeline_run_api_v1_pipelines_pipeline_id_runs_pipeline_run_id_get,
                                p.id,
                                run.id)
                            if r.status == 'Succeeded':
                                eval_path = get_eval_dir(p.id, r.id, info)
                                evaluation = tfma.load_eval_result(eval_path)
                                for s, m in evaluation.slicing_metrics:
                                    result_list.append(dict([(
                                    'pipeline_name', '{}:{}'.format(p.name, 
                                    r.id)),
                                                             ('slice_name', 
                                                             s[0][0] if s 
                                                             else ''), 
                                                             ('slice_value', 
                                                             s[0][1] if s 
                                                             else ''), 
                                                             ('metrics', 
                                                             m[''][''])]))

                                h_dict = api_call(
                                    p_api.get_hyperparameters_pipeline_api_v1_pipelines_pipeline_id_runs_pipeline_run_id_hyperparameters_get, 
                                    p.id,
                                    r.id)
                                h_dict['pipeline_name'] = '{}:{}'.format(
                                p.name, r.id)
                                hparam_list.append(h_dict)

                self.results = pd.DataFrame([parse_metrics(r) for r in 
                result_list])
                self.hparam_info = pd.DataFrame(hparam_list)

                # set params
                self.param.pipeline_run_selector.objects = self.results[
                'pipeline_name'].unique()


            def generate_results_with_additional_params(self, df, 
            track_list, pipeline_run_selector):
                print('Generating results...')
                tracking_dict = dict()
                for key in track_list:
                    component, parameter = key.split(':')
                    if component in tracking_dict:
                        tracking_dict[component].append(parameter)
                    else:
                        tracking_dict[component] = [parameter]

                context_list = list(self.results[self.results[
                'pipeline_name'].isin(pipeline_run_selector)][
                'context_id'].unique())
                for c in context_list:
                    for e in api_get_list_of_executions(int(c), info)[0]:
                        component_id = e['properties']['component_id'][
                        'stringValue']
                        if component_id in tracking_dict:
                            parameter_list = tracking_dict[component_id]
                            for p in parameter_list:
                                param_name = ':'.join([component_id, p])
                                param_value = e['properties'][p]['stringValue']
                                df.loc[df['context_id'] == c, param_name] = 
                                float(param_value)

                return df


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

                self.param['slicing_metric_selector'].objects = 
                slicing_metric_list
                self.param['performance_metric_selector'].objects = 
                performance_metric_list

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

                    dimensions = ['pipeline_name'] + 
                    self.hyperparameter_selector + [
                    self.performance_metric_selector]

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
                                                                colorscale = 
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
    '''
    return dedent(block)[:-1]


def interface_block():
    block = '''\
        def generate_interface():

            app = Application()
            handlers = pn.Param(app.param)

            # Analysis Page
            analysis_page = pn.GridSpec(height = 850, width=1850, max_height 
            = 850, max_width=1850)
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

        platform = generate_interface()
        platform.servable()
    '''
    return dedent(block)[:-1]


def get_model_block(log_dir):
    block = '''\
    import os

    model_path = '"{evaluation}"'
    logdir = os.path.join(model_path, 'logs')
    %load_ext tensorboard
    '''.format(evaluation=log_dir)
    block = dedent(block)
    block += '%tensorboard --logdir {logdir}'
    return block


def get_eval_block(eval_dir):
    block = '''\
    # If the visualization does not appear after running this block, please 
    # run the same cell again

    import tensorflow_model_analysis as tfma

    evaluation_path = '{evaluation}'
    evaluation = tfma.load_eval_result(output_path=evaluation_path)

    # find slicing metrics
    slicing_columns = set([x.feature_keys[0] for x in 
    evaluation.config.slicing_specs if len(x.feature_keys) == 1])
    print("")
    print("Available slicing columns: ")
    print(slicing_columns)

    tfma.view.render_slicing_metrics(evaluation)

    # in order to view sliced results, pass in the `slicing_column` parameter:
    # tfma.view.render_slicing_metrics(evaluation, slicing_column='col_name')
    '''.format(evaluation=eval_dir)
    return dedent(block)[:-1]
