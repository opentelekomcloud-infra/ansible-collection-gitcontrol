#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = '''
module: teams
short_description: Manage GitHub Organization Teams
extends_documentation_fragment: opentelekomcloud.gitcontrol.git
version_added: "0.0.1"
author: "Artem Goncharov (@gtema)"
description:
  - Manages team members inside of the organization repository
options:
  token:
    description: GitHub token
    type: str
    required: True
'''

RETURN = '''
'''

EXAMPLES = '''
'''


from ansible_collections.opentelekomcloud.gitcontrol.plugins.module_utils.git import GitBase


class TeamsModule(GitBase):
    argument_spec = dict(
        token=dict(type='str', required=True, no_log=True)
    )
    module_kwargs = dict(
        supports_check_mode=True
    )

    def is_team_update_necessary(self, team_dict, current_team):
        if (
            team_dict.get('description') != current_team.get('description')
        ):
            return True
        if (
            team_dict.get('privacy') != current_team.get('privacy')
        ):
            return True
        return False

    def run(self):
        status = dict()
        changed = False

        for owner, owner_dict in self.get_teams().items():
            status[owner] = dict()

            # Get current org teams
            current_teams = self.get_owner_teams(owner)
            if current_teams is None:
                self.fail_json(
                    msg=f'Cannot fetch current teams for {owner}',
                    errors=self.errors)

            # Go over teams required to exist
            for team, team_dict in owner_dict['present']['teams'].items():
                current_team = None
                team_slug = None
                if team not in [x['slug'] for x in current_teams]:
                    changed = True
                    # Create new team
                    if self.ansible.check_mode:
                        current_team = team
                    else:
                        current_team = self.create_team(
                            owner=owner,
                            name=team,
                            description=team_dict.get('description'),
                            privacy=team_dict.get('privacy'),
                            parent=team_dict.get('parent'),
                            maintainers=team_dict.get('maintainer')
                        )
                        team_slug = current_team['slug']
                else:
                    for t in current_teams:
                        if t['name'] == team:
                            current_team = t
                            team_slug = t['slug']
                            break
                    if not current_team:
                        # Not able to cope with wanted team, try others
                        continue

                status[owner][team] = dict()
                status[owner][team]['description'] = current_team

                if (
                    team_slug
                    and self.is_team_update_necessary(team_dict, current_team)
                ):
                    # Update Team
                    changed = True
                    if not self.ansible.check_mode:
                        self.update_team(owner, team_slug, **team_dict)
                    status[owner][team]['status'] = 'updated'

                if team_slug:
                    current_members = [
                        x['login'] for x in self.get_team_members(
                            owner, team_slug, role='member')
                    ]
                else:
                    current_members = []

                if team_slug:
                    current_maintainers = [
                        x['login'] for x in self.get_team_members(
                            owner, team_slug, role='maintainer')
                    ]
                else:
                    current_maintainers = []

                status[owner][team]['members'] = dict()
                for login in team_dict['member']:
                    # Member should exist
                    if login not in current_members:
                        changed = True
                        if not self.ansible.check_mode:
                            self.set_team_member(
                                owner, team_slug, login, role='member')
                        status[owner][team]['members'][login] = 'Added'
                    else:
                        status[owner][team]['members'][login] = 'Present'

                status[owner][team]['maintainers'] = dict()
                for login in team_dict['maintainer']:
                    # Maintainer should exist
                    if login not in current_maintainers:
                        changed = True
                        if not self.ansible.check_mode:
                            self.set_team_member(
                                owner, team_slug, login, role='maintainer')
                        status[owner][team]['maintainers'][login] = 'Added'
                    else:
                        status[owner][team]['maintainers'][login] = 'Present'

        if len(self.errors) == 0:
            self.exit_json(
                changed=changed,
                teams=status,
                errors=self.errors
            )
        else:
            self.fail_json(
                msg='Failures occured',
                errors=self.errors,
                teams=status
            )


def main():
    module = TeamsModule()
    module()


if __name__ == "__main__":
    main()
