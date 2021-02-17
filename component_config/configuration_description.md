
**MODE**

The app works in two modes:

- **CREATE** - creates project and invites user
- **INVITE** - Invites users to existing project (`project_id` must be included on input)

Generates projects of specified types for users defined in table: `users.csv` 
with columns:

- `email` - user email who will be invited to the new project"
- `name` - name of the project
- `features` - optional column. comma-separated list of project features
- `storage_backend` - optional column. Id of the Storage backend
- `project_id` - required when run in `INVITE` mode


Invites users (using specified email).

Outputs table `user_projects` (`["email", "project_id", "features]`)