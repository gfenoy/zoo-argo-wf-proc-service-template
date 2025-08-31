import base64
import json
import os
import pathlib
from loguru import logger
import yaml

from zoo_argowf_runner.runner import ZooArgoWorkflowsRunner

#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../zoo-runner-common')))
#from base_handler import ExecutionHandler

from common_execution_handler import CommonExecutionHandler

from zoostub import ZooStub
zoo = ZooStub()



class ArgoWFRunnerExecutionHandler(CommonExecutionHandler):
    def get_pod_env_vars(self, **kwargs):
        # sets two env vars in the pod launched by Calrissian
        return {"A": "1", "B": "1"}

    def get_pod_node_selector(self, **kwargs):
        return None

    def get_secrets(self, **kwargs):
        pass

    def get_additional_parameters(self, **kwargs):
        # sets the additional parameters for the execution
        # of the wrapped Application Package

        zoo.info("get_additional_parameters")

        additional_parameters = {
            "s3_bucket": "results",
            "sub_path": self.conf["lenv"]["usid"],
            "region_name": "it-rom",
            "aws_secret_access_key": "minio-admin",
            "aws_access_key_id": "minio-admin",
            "endpoint_url": "http://minio.ns1.svc.cluster.local:9000",
        }

        zoo.info(f"additional_parameters: {additional_parameters.keys()}")

        return additional_parameters

    def handle_outputs(self, log, output, usage_report, tool_logs, **kwargs):
        logger.info("Handling outputs")
        execution = kwargs.get("execution")

        # logger.info(f"Set output to {output['s3_catalog_output']}")
        # self.results = {"url": execution.get_feature_collection()}

        # self.conf["main"]["tmpUrl"] = self.conf["main"]["tmpUrl"].replace(
        #     "temp/", self.conf["auth_env"]["user"] + "/temp/"
        # )

        tool_logs = execution.get_tool_logs()

        services_logs = [
            {
                "url": os.path.join(
                    self.conf["main"]["tmpUrl"].replace("/temp/",f"/{self.conf['auth_env']['ouser']}/temp/"),
                    f"{self.conf['lenv']['Identifier']}-{self.conf['lenv']['usid']}",
                    os.path.basename(tool_log),
                ),
                "title": f"Tool log {os.path.basename(tool_log)}",
                "rel": "related",
            }
            for tool_log in tool_logs
        ]
        for i in range(len(services_logs)):
            okeys = ["url", "title", "rel"]
            keys = ["url", "title", "rel"]
            if i > 0:
                for j in range(len(keys)):
                    keys[j] = keys[j] + "_" + str(i)
            if "service_logs" not in self.conf:
                self.conf["service_logs"] = {}
            for j in range(len(keys)):
                self.conf["service_logs"][keys[j]] = services_logs[i][okeys[j]]

        self.conf["service_logs"]["length"] = str(len(services_logs))
        logger.info(f"service_logs: {self.conf['service_logs']}")

    #def pre_execution_hook(self, **kwargs):
    #    return super().pre_execution_hook(**kwargs)

    #def post_execution_hook(self, **kwargs):
    #    return super().post_execution_hook(**kwargs)


def {{cookiecutter.workflow_id |replace("-", "_")  }}(conf, inputs, outputs):
    with open(
        os.path.join(
            pathlib.Path(os.path.realpath(__file__)).parent.absolute(),
            "app-package.cwl",
        ),
        "r",
    ) as stream:
        cwl = yaml.safe_load(stream)

    proxy_url = os.environ.pop("HTTP_PROXY", None)
    conf["auth_env"]["ouser"]=conf["auth_env"]["user"]
    conf["auth_env"]["user"]="ns1"
    runner = ZooArgoWorkflowsRunner(
        cwl=cwl,
        conf=conf,
        inputs=inputs,
        outputs=outputs,
        execution_handler=ArgoWFRunnerExecutionHandler(conf=conf),
    )
    exit_status = runner.execute()

    if exit_status == zoo.SERVICE_SUCCEEDED:
        outputs = runner.outputs
        return zoo.SERVICE_SUCCEEDED

    else:
        conf["lenv"]["message"] = zoo._("Execution failed")
        return zoo.SERVICE_FAILED
