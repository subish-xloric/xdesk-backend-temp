
import time
import gitlab
import requests

from datetime import datetime

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs


class GitLabEngine():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()        

    def create_new_branch(self, git_uri, token, git_project_id, new_branch, source_branch, ticket_key):
        response = {"message": "", "error": False}
        try:
            gl = gitlab.Gitlab(git_uri, private_token=token)        
            project = gl.projects.get(git_project_id)
            branch = project.branches.create({'branch': new_branch, 'ref': source_branch})
            response['message'] = "New branch created"
        except Exception as e:
            response['error'] = True             
            response['message'] = f"The brach created request for ticket {ticket_key} has failed. The error is {e}. Please take the necessary actions to resolve the issues."
            self.__log.error(self.__exception.get_exception())
        return response

    def delete_branch(self, git_uri, token, git_project_id, branch_name, ticket_key):
        response = {"message": "", "error": False}
        try:
            gl = gitlab.Gitlab(git_uri, private_token=token)        
            project = gl.projects.get(git_project_id)
            branch = project.branches.get(branch_name)
            branch.delete()
            response['message'] = f"Branch '{branch_name}' deleted successfully."
        except gitlab.exceptions.GitlabGetError:
            response['message'] = f"Branch '{branch_name}' does not exist."
        except gitlab.exceptions.GitlabDeleteError as e:
            response['message'] = f"Failed to delete branch '{branch_name}'. Error: {e}"
        except Exception as e:
            response['error'] = True             
            response['message'] = f"The brach delete request for ticket {ticket_key} has failed. The error is {e}. Please take the necessary actions to resolve the issues."
            self.__log.error(self.__exception.get_exception())

    def merge_and_push(self,git_uri, token, git_project_id, source_branch, target_branch,ticket_key=''):
        response = {"message": "", "error": False}
        message_list =[]
        try:
            # Initialize GitLab connection
            gl = gitlab.Gitlab(git_uri, private_token=token)
            project = gl.projects.get(git_project_id)

            merge_request = project.mergerequests.create({
                'source_branch': source_branch,
                'target_branch': target_branch,
                'title': f'Merge {source_branch} into {target_branch} on {datetime.now().strftime("%d/%m/%Y %H:%m:%S")}',
                'description': 'Automated merge request via DM Desk',
                'remove_source_branch': True,  # Remove the source branch after merge
                #'squash':True,
                #'squash_commit_message': f'Merge {source_branch} into {target_branch} on {datetime.now().strftime("%d/%m/%Y %H:%m:%S")}',
            })
            message_list.append(f'Merge request created: {merge_request.web_url}')
            #print(f'Merge request created: {merge_request.web_url}')
            time.sleep(5)

            merge_commit_message = f'Merged {source_branch} into {target_branch} on {datetime.now().strftime("%d/%m/%Y %H:%m:%S")}'            

            if merge_request.has_conflicts:
                message_list.append(f'Merge request has conflicts: {merge_request.web_url}')                
                if self.resolve_conflicts(merge_request, project):
                    message_list.append("Conflicts resolved automatically. Proceeding to merge.")                    
                    #merge_request.approve()
                    time.sleep(10)
                    merge_request.merge(merge_commit_message=merge_commit_message, should_remove_source_branch=True)
                    message_list.append(f"The merge request for ticket {ticket_key} has accepted. {merge_commit_message}")
                    
                else:
                    response['error'] = True                   
                    message_list.append(f"The merge request for ticket {ticket_key} has conflicts. Conflicts could not be resolved automatically, Please take the necessary actions to resolve the issues")
                    
            else:
                #merge_request.approve()
                time.sleep(10)
                merge_request.merge(merge_commit_message=merge_commit_message, should_remove_source_branch=True)
                #print(f'Merge request accepted: {merge_request.title}')
                message_list.append(f"The merge request for ticket {ticket_key} has accepted. {merge_commit_message}")
                #subject = f'Merge request accepted for ticket {issue_key}'
                #self.send_email(subject, msg)
        except Exception as e:
            response['error'] = True             
            message_list.append(f"The merge request for ticket {ticket_key} has failed. The error is {e}. Please take the necessary actions to resolve the issues.")
            self.__log.error(self.__exception.get_exception())
        finally:
            response['message'] = message_list
        return response

    
    #Prefer Source Branch Changes
    def resolve_conflicts(self, merge_request, project):
        try:
            conflicts = merge_request.conflicts.list()
            for conflict in conflicts:
                #print(f"Resolving conflict in file: {conflict['new_path']}")
                source_content = project.repository_files.get(conflict['new_path'], ref=merge_request.source_branch).decode().decode()
                conflict_data = {
                    'id': conflict['id'],
                    'new_path': conflict['new_path'],
                    'content': source_content,
                    'conflict_resolution': 'prefer_source'
                }
                merge_request.conflicts.resolve(conflict_data)
            return True
        except gitlab.exceptions.GitlabError as e:
            #print(f'Error resolving conflicts: {e}')
            return False
        
    def create_new_branch_api(self, git_uri, token, git_project_id, new_branch, source_branch):

        GITLAB_API_URL = git_uri +'/api/v4'
        # API endpoint to create a new branch
        url = f"{GITLAB_API_URL}/projects/{git_project_id}/repository/branches"

        # Headers for the request
        headers = {'PRIVATE-TOKEN': token}

        # Data for the request
        data = {
            'branch': new_branch,
            'ref': source_branch
        }

        # Make the request to create the new branch
        response = requests.post(url, headers=headers, data=data)

        # Check the response
        if response.status_code == 201:
            print(f"Branch '{new_branch}' created successfully.")
        else:
            print(f"Failed to create branch: {response.status_code}")
            print(response.json())
        
        

        