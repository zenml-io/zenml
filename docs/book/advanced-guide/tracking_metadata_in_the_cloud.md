---
description: Use a MySQL Database to track your Metadata non-locally 
---

# Track your Metadata in the Cloud

While the local SQLite-based Metadata store is a great default to get you 
started quickly, you will need to move towards a deployed, shared and scalable
database once you switch to remote orchestration at the latest. 
This database will ideally be accessible both from your local machine, your 
orchestrator and the individual worker nodes of your orchestrator. 
A deployed MySQL Database can tick all these boxes. 

## Registering the MySQL Metadata Store