from __future__ import annotations

import logging
from typing import Dict, List, Union
from typing import TYPE_CHECKING

import httpx

from cs_tools.api._client import RESTAPIClient
from cs_tools.api._utils import scrub_undefined
from cs_tools.types import DeployType, DeployPolicy, GUID, MetadataObjectType

if TYPE_CHECKING:
    Identifier = Union[GUID, int, str]

log = logging.getLogger(__name__)


class RESTAPIv2(RESTAPIClient):
    """
    Implementation of the REST API v2.
    """

    def request(self, method: str, endpoint: str, **request_kw) -> httpx.Response:
        request_kw = scrub_undefined(request_kw, null=None)
        return super().request(method, endpoint, **request_kw)

    # ==================================================================================================================
    # AUTHENTICATION ::  https://developers.thoughtspot.com/docs/rest-api-getstarted#_authentication
    # ==================================================================================================================

    def auth_session_login(self, username: str, password: str, org_identifier: str = None, remember_me: bool = False) -> httpx.Response:
        body = {
            "username": username,
            "password": password,
            "org_identifier": org_identifier,
            "remember_me": remember_me
        }
        r = self.post("api/rest/2.0/auth/session/login", json=body)
        return r

    def auth_session_user(self) -> httpx.Response:
        r = self.get("api/rest/2.0/auth/session/user")
        return r

    # ==================================================================================================================
    # VERSION CONTROL     ::  https://developers.thoughtspot.com/docs/rest-apiv2-reference#_version_control_beta
    # ==================================================================================================================

    def vcs_git_config_create(self,
                              *,
                              repository_url: str,
                              username: str,
                              access_token: str,
                              org_identifier: Identifier,
                              branch_names: List[str] = None,
                              commit_branch_name: str = None,
                              enable_guid_mapping: bool = False,
                              configuration_branch_name: str
                              ) -> httpx.Response:
        body= {
            "repository_url": repository_url,
            "username": username,
            "access_token": access_token,
            "org_identifier": org_identifier,
            "branch_names": branch_names,
            "commit_branch_name": commit_branch_name,
            "enable_guid_mapping": enable_guid_mapping,
            "configuration_branch_name": configuration_branch_name
        }

        r = self.post("api/rest/2.0/vcs/git/config/create", json=body)
        return r

    def vcs_git_config_update(self,
                              *,
                              username: str,
                              access_token: str,
                              org_identifier: Identifier = None,
                              branch_names: List[str] = None,
                              commit_branch_name: str = None,
                              enable_guid_mapping: bool = False,
                              configuration_branch_name: str = None
                              ) -> httpx.Response:
        body= {
            "username": username,
            "access_token": access_token,
            "org_identifier": org_identifier,
            "branch_names": branch_names,
            "commit_branch_name": commit_branch_name,
            "enable_guid_mapping": enable_guid_mapping,
            "configuration_branch_name": configuration_branch_name
        }
        r = self.post("api/rest/2.0/vcs/git/config/update", json=body)
        return r

    def vcs_git_config_search(self, *, org_ids: List[Identifier] = None) -> httpx.Response:
        body= {"org_identifiers": org_ids}
        r = self.post("api/rest/2.0/vcs/git/config/search", json=body)
        return r

    def vcs_git_config_delete(self, *, cluster_level: bool = False) -> httpx.Response:
        body = {
            "cluster_level": cluster_level
        }
        r = self.post("api/rest/2.0/vcs/git/config/delete", json=body)
        return r

    def vcs_git_branches_commit(self,
                                *,
                                metadata: List[Dict],
                                branch_name: str = None,
                                delete_aware: bool = False,
                                comment: str
                                ) -> httpx.Response:
        body = {
            "metadata": metadata,
            "branch_name": branch_name,
            "comment": comment,
            "delete_aware": delete_aware
        }
        r = self.post("api/rest/2.0/vcs/git/branches/commit", json=body)
        return r

    def vcs_git_commits_search(self,
                               *,
                               metadata_identifier: Identifier,
                               metadata_type: MetadataObjectType,
                               branch_name: str = None,
                               record_offset: int = 0,
                               record_size: int = -1,  # -1 means all.
                               ) -> httpx.Response:
        body = {
            "metadata_identifier": metadata_identifier,
            "metadata_type": metadata_type,
            "branch_name": branch_name,
            "record_offset": record_offset,
            "record_size": record_size
        }
        r = self.post(f"api/rest/2.0/vcs/git/commits/search", json=body)
        return r

    def vcs_git_commits_id_revert(self,
                                  *,
                                  commit_id: str,
                                  metadata: List[Dict],
                                  branch_name: str,
                                  revert_policy: DeployPolicy = DeployPolicy.all_or_none
                                  ) -> httpx.Response:
        body = {
            "metadata": metadata,
            "branch_name": branch_name,
            "revert_policy": revert_policy
        }
        r = self.post(f"api/rest/2.0/vcs/git/commits/{commit_id}/revert", json=body)
        return r

    def vcs_git_branches_validate(self,
                                  *,
                                  source_branch_name: str,
                                  target_branch_name: str,
                                  ) -> httpx.Response:
        body = {
            "source_branch_name": source_branch_name,
            "target_branch_name": target_branch_name,
        }
        r = self.post("api/rest/2.0/vcs/git/branches/validate", json=body)
        return r

    def vcs_git_commits_deploy(self, *,
                               commit_id: str,
                               branch_name: str,
                               deploy_type: DeployType = DeployType.delta,
                               deploy_policy: DeployPolicy = DeployPolicy.all_or_none
                               ) -> httpx.Response:
        body = {
            "commit_id": commit_id,
            "branch_name": branch_name,
            "deploy_type": str(deploy_type),
            "deploy_policy": str(deploy_policy)
        }
        r = self.post("api/rest/2.0/vcs/git/commits/deploy", json=body)
        return r
