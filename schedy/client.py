from .core import Core, Config
from .projects import Projects


class Client(object):

    def __init__(self, config_path=None, config_override=None):
        """
           Client is the central component of Schedy. It represents your
           connection the the Schedy service.

           Args:
               config_path (str or file-object): Path to the client configuration file. This file
                   contains your credentials (email, API token). By default,
                   ~/.schedy/client.json is used. See :ref:`setup` for
                   instructions about how to use this file.
               config_override (dict): Content of the configuration. You can use this to
                   if you do not want to use a configuration file.
        """
        self.config = Config(config_path, config_override)
        self._core = Core(self.config)

        self.projects = Projects(self._core)

    def create_project(self, project_id, project_name):
        return self.projects.create(project_id, project_name)

    def get_project(self, project_id):
        return self.projects.get(project_id)

    def get_projects(self):
        return self.projects.get_all()

    def delete_project(self, project_id):
        return self.projects.delete(project_id)
