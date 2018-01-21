POLICIES = [
    # Policies
    {
        "name": "policies:get",
        "description": "Ability to get a policy",
        "tags": [
            "viewer"
        ]

    },
    {
        "name": "policies:list",
        "description": "Ability to list policies",
        "tags": [
            "viewer"
        ]
    },

    # Roles
    {
        "name": "roles:create:global",
        "description": "Ability to create a global role"
    },
    {
        "name": "roles:delete:global",
        "description": "Ability to delete a global role"
    },
    {
        "name": "roles:create:project",
        "description": "Ability to create a project role",
        "tags": [
            "project_member"
        ]
    },
    {
        "name": "roles:delete:project",
        "description": "Ability to delete a project role",
        "tags": [
            "project_member"
        ]
    },
    {
        "name": "roles:get",
        "description": "Ability to get a role",
        "tags": [
            "viewer"
        ]
    },
    {
        "name": "roles:list",
        "description": "Ability to list roles",
        "tags": [
            "viewer"
        ]
    },

    # Flavors
    {
        "name": "flavors:create",
        "description": "Ability to create a flavor",
    },
    {
        "name": "flavors:get",
        "description": "Ability to get a flavor",
        "tags": [
            "viewer",
            "service_account"
        ]
    },
    {
        "name": "flavors:list",
        "description": "Ability to list flavors",
        "tags": [
            "viewer",
            "service_account"
        ]
    },
    {
        "name": "flavors:delete",
        "description": "Ability to delete a flavor",
    },

    # Regions
    {
        "name": "regions:create",
        "description": "Ability to create a region"
    },
    {
        "name": "regions:get",
        "description": "Ability to get a region",
        "tags": [
            "viewer"
        ]
    },
    {
        "name": "regions:list",
        "description": "Ability to list regions",
        "tags": [
            "viewer"
        ]
    },
    {
        "name": "regions:delete",
        "description": "Ability to delete a region"
    },
    {
        "name": "regions:action:schedule",
        "description": "Ability to change the schedule mode of the region"
    },

    # Zones
    {
        "name": "zones:create",
        "description": "Ability to create a zone"
    },
    {
        "name": "zones:get",
        "description": "Ability to get a zone",
        "tags": [
            "viewer"
        ]
    },
    {
        "name": "zones:list",
        "description": "Ability to list zones",
        "tags": [
            "viewer"
        ]
    },
    {
        "name": "zones:delete",
        "description": "Ability to delete a zone"
    },
    {
        "name": "zones:action:schedule",
        "description": "Ability to change the schedule mode of the zone"
    },

    # Projects
    {
        "name": "projects:create",
        "description": "Ability to create a project"
    },
    {
        "name": "projects:get",
        "description": "Ability to get a project",
        "tags": [
            "viewer"
        ]
    },
    {
        "name": "projects:get:all",
        "description": "Ability to get all projects"
    },
    {
        "name": "projects:list",
        "description": "Ability to list projects",
        "tags": [
            "viewer"
        ]
    },
    {
        "name": "projects:list:all",
        "description": "Ability to list all projects"
    },
    {
        "name": "projects:delete",
        "description": "Ability to delete a project"
    },
    {
        "name": "projects:scope",
        "description": "Ability to scope to projects"
    },
    {
        "name": "projects:scope:all",
        "description": "Ability to scope to all projects"
    },
    {
        "name": "projects:members:add",
        "description": "Ability to add a member to a project",
        "tags": [
            "project_member"
        ]
    },
    {
        "name": "projects:members:get",
        "description": "Ability to get a member in a project",
        "tags": [
            "project_member"
        ]
    },
    {
        "name": "projects:members:list",
        "description": "Ability to list members in a project",
        "tags": [
            "project_member",
            "service_account"
        ]
    },
    {
        "name": "projects:members:modify",
        "description": "Ability to modify a project member's roles",
        "tags": [
            "project_member"
        ]
    },
    {
        "name": "projects:members:remove",
        "description": "Ability to remove a member from a project",
        "tags": [
            "project_member"
        ]
    },
    {
        "name": "projects:quota:get",
        "description": "Ability to get a project's quota",
        "tags": [
            "project_member",
            "service_account"
        ]
    },
    {
        "name": "projects:quota:modify",
        "description": "Ability to modify a project's quota",
    },
    # Volumes
    {
        "name": "volumes:create",
        "description": "Ability to create a volume"
    },
    {
        "name": "volumes:get",
        "description": "Ability to get a volume",
        "tags": [
            "project_member",
            "service_account"
        ]
    },
    {
        "name": "volumes:list",
        "description": "Ability to list volumes",
        "tags": [
            "project_member",
            "service_account"
        ]
    },
    {
        "name": "volumes:delete",
        "description": "Ability to delete a volume",
        "tags": [
            "project_member"
        ]
    },
    {
        "name": "volumes:action:attach",
        "description": "Ability to attach a volume to an instance",
        "tags": [
            "project_member"
        ]
    },
    {
        "name": "volumes:action:detach",
        "description": "Ability to detach a volume from an instance",
        "tags": [
            "project_member"
        ]
    },
    {
        "name": "volumes:action:grow",
        "description": "Ability to grow a volume",
        "tags": [
            "project_member"
        ]
    },
    {
        "name": "volumes:action:clone",
        "description": "Ability to clone a volume",
        "tags": [
            "project_member"
        ]
    },

    # Images
    {
        "name": "images:create",
        "description": "Ability to create an image"
    },
    {
        "name": "images:get",
        "description": "Ability to get an image",
        "tags": [
            "project_member",
            "service_account"
        ]
    },
    {
        "name": "images:list",
        "description": "Ability to list images",
        "tags": [
            "project_member",
            "service_account"
        ]
    },
    {
        "name": "images:delete",
        "description": "Ability to delete an image",
        "tags": [
            "project_member"
        ]
    },
    {
        "name": "images:action:visibility",
        "description": "Ability to change the image visibility",
        "tags": [
            "project_member"
        ]
    },
    {
        "name": "images:action:visibility:public",
        "description": "Ability to change the image visibility to public"
    },
    {
        "name": "images:action:lock",
        "description": "Ability to lock an image",
        "tags": [
            "project_member"
        ]
    },
    {
        "name": "images:action:unlock",
        "description": "Ability to unlock an image",
        "tags": [
            "project_member"
        ]
    },
    {
        "name": "images:members:add",
        "description": "Ability to add a member to an image",
        "tags": [
            "project_member"
        ]
    },
    {
        "name": "images:members:list",
        "description": "Ability to list image members",
        "tags": [
            "project_member"
        ]
    },
    {
        "name": "images:members:delete",
        "description": "Ability to delete a member from an image",
        "tags": [
            "project_member"
        ]
    },

    # Instances
    {
        "name": "instances:create",
        "description": "Ability to create an instance",
        "tags": [
            "project_member"
        ]
    },
    {
        "name": "instances:get",
        "description": "Ability to get an instance",
        "tags": [
            "project_member",
            "service_account"
        ]
    },
    {
        "name": "instances:list",
        "description": "Ability to list instances",
        "tags": [
            "project_member",
            "service_account"
        ]
    },
    {
        "name": "instances:delete",
        "description": "Ability to delete an instance",
        "tags": [
            "project_member"
        ]
    },
    {
        "name": "instances:action:stop",
        "description": "Ability to stop an instance",
        "tags": [
            "project_member"
        ]
    },
    {
        "name": "instances:action:start",
        "description": "Ability to start an instance",
        "tags": [
            "project_member"
        ]
    },
    {
        "name": "instances:action:restart",
        "description": "Ability to restart an instance",
        "tags": [
            "project_member"
        ]
    },
    {
        "name": "instances:action:image",
        "description": "Ability to create an image from an instance",
        "tags": [
            "project_member"
        ]
    },
    {
        "name": "instances:action:reset_state",
        "description": "Ability to reset the state of an instance to error",
        "tags": [
            "project_member"
        ]
    },
    {
        "name": "instances:action:reset_state:active",
        "description": "Ability to reset the state of an instance to active",
        "tags": [
            "project_member"
        ]
    },

    # Networks
    {
        "name": "networks:create",
        "description": "Ability to create a network"
    },
    {
        "name": "networks:get",
        "description": "Ability to get a network",
        "tags": [
            "viewer"
        ]
    },
    {
        "name": "networks:list",
        "description": "Ability to list networks",
        "tags": [
            "viewer"
        ]
    },
    {
        "name": "networks:delete",
        "description": "Ability to delete a network"
    },

    # Service Accounts
    {
        "name": "service_accounts:create",
        "description": "Ability to create a service account",
        "tags": [
            "project_member"
        ]
    },
    {
        "name": "service_accounts:get",
        "description": "Ability to get a service account",
        "tags": [
            "project_member",
            "service_account"
        ]
    },
    {
        "name": "service_accounts:list",
        "description": "Ability to list service accounts",
        "tags": [
            "project_member",
            "service_account"
        ]
    },
    {
        "name": "service_accounts:delete",
        "description": "Ability to delete a service account",
        "tags": [
            "project_member"
        ]
    },

    # Database Users
    {
        "name": "database:users:create",
        "description": "Ability to create users",
    },
    {
        "name": "database:users:get",
        "description": "Ability to get a user"
    },
    {
        "name": "database:users:list",
        "description": "Ability to list users"
    },
    {
        "name": "database:users:delete",
        "description": "Ability to delete a user"
    },
    {
        "name": "database:users:password",
        "description": "Ability to change a user's password"
    },
    {
        "name": "database:users:role:add",
        "description": "Ability to add a role to a user"
    },
    {
        "name": "database:users:role:remove",
        "description": "Ability to remove a user from a role"
    },

    # Keypairs
    {
        "name": "keypairs:create",
        "description": "Ability to create a keypair",
        "tags": [
            "project_member"
        ]
    },
    {
        "name": "keypairs:get",
        "description": "Ability to get a keypair",
        "tags": [
            "project_member",
            "service_account"
        ]
    },
    {
        "name": "keypairs:list",
        "description": "Ability to list keypairs",
        "tags": [
            "project_member",
            "service_account"
        ]
    },
    {
        "name": "keypairs:delete",
        "description": "Ability to delete a keypair",
        "tags": [
            "project_member"
        ]
    },

    # Network Ports
    {
        "name": "network_ports:get",
        "description": "Ability to get a network port",
        "tags": [
            "project_member",
            "service_account"
        ]
    },
    {
        "name": "network_ports:list",
        "description": "Ability to list  network ports",
        "tags": [
            "project_member",
            "service_account"
        ]
    },
    {
        "name": "network_ports:delete",
        "description": "Ability to delete a network port",
        "tags": [
            "project_member"
        ]
    }]
