import base64
import json
import os
import pathlib
from loguru import logger
import yaml

from zoo_argowf_runner.runner import ExecutionHandler, ZooArgoWorkflowsRunner


try:
    import zoo
except ImportError:

    class ZooStub(object):
        def __init__(self):
            self.SERVICE_SUCCEEDED = 3
            self.SERVICE_FAILED = 4

        def update_status(self, conf, progress):
            print(f"Status {progress}")

        def _(self, message):
            print(f"invoked _ with {message}")

    zoo = ZooStub()


class ArgoWFRunnerExecutionHandler(ExecutionHandler):
    def get_pod_env_vars(self):
        logger.info("get_pod_env_vars")

        env_vars: Dict[str, str] = {}
        env_vars = self.conf.get("pod_env_vars", {})

        return env_vars

    def get_pod_node_selector(self):
        logger.info("get_pod_node_selector")
        node_selector: Dict[str, str] = {}
        node_selector = self.conf.get("pod_node_selector", {})

        logger.info(f"node_selector: {node_selector.keys()}")

        return node_selector

    def get_secrets(self):
        logger.info("get_secrets")
        secrets={
            "imagePullSecrets": self.local_get_file("/assets/pod_imagePullSecrets.yaml"),
            "additionalImagePullSecrets": self.local_get_file("/assets/pod_additionalImagePullSecrets.yaml")
        }
        return secrets

    def get_additional_parameters(self):
        # sets the additional parameters for the execution
        # of the wrapped Application Package

        logger.info("get_additional_parameters")
        additional_parameters: Dict[str, str] = {}
        additional_parameters = self.conf.get("additional_parameters", {})

        additional_parameters["sub_path"] = self.conf["lenv"]["usid"]

        logger.info(f"additional_parameters: {additional_parameters.keys()}")

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

    def pre_execution_hook(self, **kwargs):
        return super().pre_execution_hook(**kwargs)

    def post_execution_hook(self, **kwargs):
        return super().post_execution_hook(**kwargs)


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
    conf["argo"]={
        "namespace":
            os.environ.get("ARGO_WF_NAMESPACE", "argo")
    }
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
