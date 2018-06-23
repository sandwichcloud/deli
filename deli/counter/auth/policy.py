SYSTEM_POLICIES = [
    # Roles
    {
        "name": "roles:system:create",
        "description": "Ability to create a system role"
    },
    {
        "name": "roles:system:get",
        "description": "Ability to get a system role",
    },
    {
        "name": "roles:system:list",
        "description": "Ability to list system roles",
    },
    {
        "name": "roles:system:update",
        "description": "Ability to update a system role",
    },
    {
        "name": "roles:system:delete",
        "description": "Ability to delete a system role"
    },
    # Flavors
    {
        "name": "flavors:create",
        "description": "Ability to create a flavor",
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
        "name": "zones:delete",
        "description": "Ability to delete a zone"
    },
    {
        "name": "zones:action:schedule",
        "description": "Ability to change the schedule mode of the zone"
    },
    # Networks
    {
        "name": "networks:create",
        "description": "Ability to create a network"
    },
    {
        "name": "networks:delete",
        "description": "Ability to delete a network"
    },
    # Projects
    {
        "name": "projects:create",
        "description": "Ability to create a project"
    },
    {
        "name": "projects:quota:modify",
        "description": "Ability to modify a project's quota",
    },
    # Service Accounts
    {
        "name": "service_accounts:system:create",
        "description": "Ability to create a system service account"
    },
    {
        "name": "service_accounts:system:get",
        "description": "Ability to get a system service account"
    },
    {
        "name": "service_accounts:system:list",
        "description": "Ability to list system service accounts"
    },
    {
        "name": "service_accounts:system:update",
        "description": "Ability to update a system service account"
    },

    {
        "name": "service_accounts:system:delete",
        "description": "Ability to delete a system service account"
    },
    {
        "name": "service_accounts:system:key:create",
        "description": "Ability to create keys for system service accounts"
    },
    {
        "name": "service_accounts:system:key:delete",
        "description": "Ability to delete keys from system service accounts"
    },
]

PROJECT_POLICIES = [
    # Project
    {
        "name": "projects:get",
        "description": "Ability to get a project",
        "tags": [
            'viewer',
            'editor'
        ]
    },
    {
        "name": "projects:delete",
        "description": "Ability to delete a project"
    },
    {
        "name": "projects:quota:get",
        "description": "Ability to get a project's quota",
        "tags": [
            'viewer',
            'editor'
        ]
    },
    # Roles
    {
        "name": "roles:project:create",
        "description": "Ability to create a project role",
        "tags": [
            'editor'
        ]
    },
    {
        "name": "roles:project:get",
        "description": "Ability to get a project role",
        "tags": [
            'viewer',
            'editor'
        ]
    },
    {
        "name": "roles:project:list",
        "description": "Ability to list project roles",
        "tags": [
            'viewer',
            'editor'
        ]
    },
    {
        "name": "roles:project:update",
        "description": "Ability to update a project role",
        "tags": [
            'editor'
        ]
    },
    {
        "name": "roles:project:delete",
        "description": "Ability to delete a project role",
        "tags": [
            'editor'
        ]
    },
    # Volumes
    {
        "name": "volumes:create",
        "description": "Ability to create a volume",
        "tags": [
            'editor'
        ]
    },
    {
        "name": "volumes:get",
        "description": "Ability to get a volume",
        "tags": [
            'viewer',
            'editor'
        ]
    },
    {
        "name": "volumes:list",
        "description": "Ability to list volumes",
        "tags": [
            'viewer',
            'editor'
        ]
    },
    {
        "name": "volumes:delete",
        "description": "Ability to delete a volume",
        "tags": [
            'editor'
        ]
    },
    {
        "name": "volumes:action:attach",
        "description": "Ability to attach a volume to an instance",
        "tags": [
            'editor'
        ]
    },
    {
        "name": "volumes:action:detach",
        "description": "Ability to detach a volume from an instance",
        "tags": [
            'editor'
        ]
    },
    {
        "name": "volumes:action:grow",
        "description": "Ability to grow a volume",
        "tags": [
            'editor'
        ]
    },
    {
        "name": "volumes:action:clone",
        "description": "Ability to clone a volume",
        "tags": [
            'editor'
        ]
    },
    # Images
    {
        "name": "images:create",
        "description": "Ability to create an image",
        "tags": [
            'editor'
        ]
    },
    {
        "name": "images:get",
        "description": "Ability to get an image",
        "tags": [
            'viewer',
            'editor'
        ]
    },
    {
        "name": "images:list",
        "description": "Ability to list images",
        "tags": [
            'viewer',
            'editor'
        ]
    },
    {
        "name": "images:delete",
        "description": "Ability to delete an image",
        "tags": [
            'editor'
        ]
    },
    {
        "name": "images:action:lock",
        "description": "Ability to lock an image",
        "tags": [
            'editor'
        ]
    },
    {
        "name": "images:action:unlock",
        "description": "Ability to unlock an image",
        "tags": [
            'editor'
        ]
    },
    # Instances
    {
        "name": "instances:create",
        "description": "Ability to create an instance",
        "tags": [
            'editor'
        ]
    },
    {
        "name": "instances:get",
        "description": "Ability to get an instance",
        "tags": [
            'viewer',
            'editor'
        ]
    },
    {
        "name": "instances:list",
        "description": "Ability to list instances",
        "tags": [
            'viewer',
            'editor'
        ]
    },
    {
        "name": "instances:delete",
        "description": "Ability to delete an instance",
        "tags": [
            'editor'
        ]
    },
    {
        "name": "instances:action:stop",
        "description": "Ability to stop an instance",
        "tags": [
            'editor'
        ]
    },
    {
        "name": "instances:action:start",
        "description": "Ability to start an instance",
        "tags": [
            'editor'
        ]
    },
    {
        "name": "instances:action:restart",
        "description": "Ability to restart an instance",
        "tags": [
            'editor'
        ]
    },
    {
        "name": "instances:action:image",
        "description": "Ability to create an image from an instance",
        "tags": [
            'editor'
        ]
    },
    # Service Accounts
    {
        "name": "service_accounts:project:create",
        "description": "Ability to create a project service account",
        "tags": [
            'editor'
        ]
    },
    {
        "name": "service_accounts:project:get",
        "description": "Ability to get a project service account",
        "tags": [
            'viewer',
            'editor'
        ]
    },
    {
        "name": "service_accounts:project:list",
        "description": "Ability to list project service accounts",
        "tags": [
            'viewer',
            'editor'
        ]
    },
    {
        "name": "service_accounts:project:update",
        "description": "Ability to update a project service account",
        "tags": [
            'editor'
        ]
    },

    {
        "name": "service_accounts:project:delete",
        "description": "Ability to delete a project service account",
        "tags": [
            'editor'
        ]
    },
    {
        "name": "service_accounts:project:key:create",
        "description": "Ability to create keys for project service accounts",
        "tags": [
            'editor'
        ]
    },
    {
        "name": "service_accounts:project:key:delete",
        "description": "Ability to delete keys from project service accounts",
        "tags": [
            'editor'
        ]
    },
    # Keypairs
    {
        "name": "keypairs:create",
        "description": "Ability to create a keypair",
        "tags": [
            'editor'
        ]
    },
    {
        "name": "keypairs:get",
        "description": "Ability to get a keypair",
        "tags": [
            'viewer',
            'editor'
        ]
    },
    {
        "name": "keypairs:list",
        "description": "Ability to list keypairs",
        "tags": [
            'viewer',
            'editor'
        ]
    },
    {
        "name": "keypairs:delete",
        "description": "Ability to delete a keypair",
        "tags": [
            'editor'
        ]
    },
    # Network Ports
    {
        "name": "network_ports:get",
        "description": "Ability to get a network port",
        "tags": [
            'viewer',
            'editor'
        ]
    },
    {
        "name": "network_ports:list",
        "description": "Ability to list  network ports",
        "tags": [
            'viewer',
            'editor'
        ]
    },
    {
        "name": "network_ports:delete",
        "description": "Ability to delete a network port",
        "tags": [
            'editor'
        ]
    },
]
