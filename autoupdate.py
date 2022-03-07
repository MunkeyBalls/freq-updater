from typing import Dict
from pathlib import Path
from shutil import copy, copyfile, copytree
import os, logging, subprocess, git, json, requests

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger(__name__)
logger.debug('Starting update script...')

class Updater:
    
    def __init__(self) -> None:
        self.load_config()
        self.init_telegram()
    
    def load_config(self):
        config = Path(__file__).parent.resolve() / "config.json"
        try:
            if not config.is_file():
                raise Exception(f"Config file {config} not found")
                
            with open(config, 'r') as jsonfile:
                jsondata = ''.join(line for line in jsonfile if not line.startswith('//'))                
                self.config = json.loads(jsondata)
        except json.JSONDecodeError as error:
            raise('Failed to parse config.json: ' + repr(error))
    
    def init_telegram(self):
        telegram = self.config.get("telegram", False)
        if telegram:
            self.telegram_url = "https://api.telegram.org/bot" + telegram['token'] + "/sendMessage" + "?chat_id=" + telegram['chat_id'] + "&text="
        else:
            self.telegram_url = None

    def run(self):        
        for repo in self.config['repositories']:
            if self.update_repo(repo):
                for bot in repo["bots"]:                
                    self.update_bot(repo, bot)

    
    def update_repo(self, repo) -> bool:
        updated = False
        
        try:
            directory = repo['directory']
            branch = repo.get('branch', None)
            url = repo.get('url', None)

            if Path(directory).is_dir():
                updated = self.git_pull(directory)
            elif url != None:
                updated = self.git_clone(url, directory, branch=branch)
            else:
                self.notify(f"Repo directory {directory} doesn't exist and URL isn't specified") # Generic catch to send exception to telegram
                raise Exception(f"Repo directory {directory} doesn't exist and URL isn't specified")        
        except git.exc.InvalidGitRepositoryError:
            self.notify(f"Update failed, directory {repo['directory']} does not contain a valid git respository")            

        return updated;   

    def git_clone(self, url: str, directory: str, branch: str):
        self.notify(f"Cloning repo {url} to {directory}")
        if branch is not None:
            git.Repo.clone_from(url, directory, branch=branch)
        else:
            git.Repo.clone_from(url, directory)
        return True

    def git_pull(self, directory: str):
        repo = git.Repo(directory)
        current = repo.head.commit     
        repo.remotes.origin.pull()

        if current == repo.head.commit:
            logger.info(f"Repo {directory} is already up to date")            
            #----------------------------------------------------------------DEBUG----------------------------------------------------------------#
            #return True
            #----------------------------------------------------------------DEBUG----------------------------------------------------------------#
            return False
        else:
            self.notify(f"{directory} updated from {current} to {repo.head.commit} latest commit: {repo.head.commit.message}")
            return True
    
    def update_bot(self, repo: Dict, bot: Dict):        
        
        self.notify(f"Updating bot: {bot['name']} in {bot['directory']}")

        if repo.get('files', False):
           for file in repo["files"]:
               self.copy_files(repo, bot, file)

        if bot.get('files', False):
           for file in bot["files"]:
               self.copy_files(repo, bot, file)
        
        self.bot_reload_config(bot)
        #self.docker_reload(bot['name'])
    
    def copy_files(self, repo: Dict, bot: Dict, file: Dict):
        repo_dir = repo["directory"]
        bot_dir = bot["directory"]

        file_src = file['file_src']
        file_dst = file.get('file_dst', None)

        src = f"{repo_dir}/{file_src}"
        
        if Path(src).is_dir(): # Copy full directory
            if file_dst != None: 
                dst = f"{bot_dir}/{file_dst}"
            else:
                dst = bot_dir
            logger.info(f"    Copying folder: {src} to {dst}")
            copytree(src, dst, symlinks=False, ignore=None, ignore_dangling_symlinks=False, dirs_exist_ok=True)
        else:
            dst = f"{bot_dir}/{file.get('file_dst', file_src)}"
            if Path(dst).is_dir():
                dst = f"{dst}/{file_src}" # Copy file to directory using orignal filename if file_dst is dir
            Path(os.path.dirname(dst)).mkdir(parents=True, exist_ok=True)
            logger.info(f"    Copying file: {src} to {dst}")
            copyfile(src, dst)

    def bot_reload_config(self, bot):
        api = bot.get('api', self.config.get('api', False))
        if api:        
            address = bot['api']['address']
            user = api['user']
            passwd = api['pass']
            endpoint = f"{address}/api/v1/reload_config"
            verify_ssl = api.get('verify_ssl')
            logger.warning(f"Reloading config {endpoint}")

            response = requests.post(endpoint, auth=(user, passwd), verify=verify_ssl)
            logger.warning(response) 
            #TODO: Check response, notify

    # def docker_reload(self, container: str = None):
    #     if self.config.get("compose_file", False):
    #         logger.info(f"Reloading docker")
    #         if container != None:
    #             command = ["docker-compose", "-f", self.config["compose_file"], "restart", container]
    #         else:
    #             command = ["docker-compose", "-f", self.config["compose_file"], "restart"]

    #         subprocess.Popen(command)

            # if (subprocess.call(command, args) == 0):
            #         print("We are proceeding)
            # else:
            #     print("Something went wrong executing %s" % command)            
            #a.wait()

    def notify(self, text: str):        
        logger.info(text)
        if self.telegram_url != None:
            url_req = self.telegram_url + text
            requests.get(url_req)        

updater = Updater()
updater.run()