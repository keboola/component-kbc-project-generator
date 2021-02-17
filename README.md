# KBC Project generator

**MODE**

The app works in two modes:

- **CREATE** - creates project and invites user
- **INVITE** - Invites users to existing project (`project_id` must be included on input)

Generates projects of specified types for users defined in table: `users.csv` 
with columns:

- `email` - user email who will be invited to the new project, or semicolon separated list of emails
- `name` - name of the project (required for CREATE mode)
- `features` - optional column. comma-separated list of project features
- `storage_backend` - optional column. Id of the Storage backend
- `project_id` - required when run in `INVITE` mode


Invites users (using specified email).

Outputs table `user_projects` (`["email", "project_id", "features]`)




## Development

If required, change local data folder (the `CUSTOM_FOLDER` placeholder) path to your custom path in the docker-compose file:

```yaml
    volumes:
      - ./:/code
      - ./CUSTOM_FOLDER:/data
```

Clone this repository, init the workspace and run the component with following command:

```
git clone repo_path my-new-component
cd my-new-component
docker-compose build
docker-compose run --rm dev
```

Run the test suite and lint check using this command:

```
docker-compose run --rm test
```

# Integration

For information about deployment and integration with KBC, please refer to the [deployment section of developers documentation](https://developers.keboola.com/extend/component/deployment/) 