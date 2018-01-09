#!/usr/bin/env bash

curl -H "Content-Type: application/json" -d "{\"source_type\": \"Tag\", \"source_name\": \"$TRAVIS_TAG\"}" -X POST "$COUNTER_DOCKER_HUB_TRIGGER"
curl -H "Content-Type: application/json" -d "{\"source_type\": \"Tag\", \"source_name\": \"$TRAVIS_TAG\"}" -X POST "$MANAGER_DOCKER_HUB_TRIGGER"
curl -H "Content-Type: application/json" -d "{\"source_type\": \"Tag\", \"source_name\": \"$TRAVIS_TAG\"}" -X POST "$MENU_DOCKER_HUB_TRIGGER"