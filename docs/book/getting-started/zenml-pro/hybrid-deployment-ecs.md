---
description: Deploy ZenML Pro Hybrid on AWS ECS with a managed control plane.
layout:
  title:
    visible: true
  description:
    visible: true
  tableOfContents:
    visible: true
  outline:
    visible: true
  pagination:
    visible: true
---

# Hybrid Deployment on AWS ECS

This guide provides high-level instructions for deploying ZenML Pro in a Hybrid setup on AWS ECS (Elastic Container Service).

## Architecture Overview

In this setup:
- **ZenML workspace** runs in ECS tasks within your VPC
- **Load balancer** handles HTTPS traffic and routes to ECS tasks
- **Database** stores workspace metadata in AWS RDS
- **Secrets manager** stores Pro credentials securely
- **NAT gateway** enables outbound access to ZenML Cloud control plane

## Prerequisites

Before starting, complete the setup described in [Hybrid Deployment Overview](hybrid-deployment.md):
- Step 1: Set up ZenML Pro organization
- Step 2: Configure your infrastructure (database, networking, TLS)
- Step 3: Obtain Pro credentials from ZenML Support

You'll also need:
- AWS Account with appropriate IAM permissions
- Basic familiarity with AWS ECS, VPC, and RDS

## Step 1: Set Up AWS Infrastructure

### VPC and Subnets

Create a VPC with:
- **Public subnets** (at least 2 across different availability zones) - for the Application Load Balancer
- **Private subnets** (at least 2 across different availability zones) - for ECS tasks and RDS

### Security Groups

Create three security groups:

1. **ALB Security Group**
   - Inbound: HTTPS (443) and HTTP (80) from `0.0.0.0/0`
   - Outbound: HTTP (8000) to the ECS security group

2. **ECS Security Group**
   - Inbound: HTTP (8000) from the ALB security group
   - Outbound: HTTPS (443) to `0.0.0.0/0` (for ZenML Cloud access)
   - Outbound: TCP (3306 for MySQL) to the RDS security group

3. **RDS Security Group**
   - Inbound: TCP (3306 for MySQL) from the ECS security group
   - Outbound: Not restricted

### NAT Gateway

To enable ECS tasks to reach ZenML Cloud:

1. Create an Elastic IP in your AWS region
2. Create a NAT Gateway in one of your public subnets
3. Wait for the NAT Gateway to be available

### Route Tables

For your private subnets (where ECS tasks run):
1. Create a route table
2. Add a default route (`0.0.0.0/0`) pointing to the NAT Gateway
3. Associate this route table with your private subnets

## Step 2: Set Up RDS Database

Create an RDS database instance. **Important**: Workspace servers only support MySQL, not PostgreSQL.

**Configuration:**
- **DB Engine**: MySQL 8.0+ (PostgreSQL is not supported for workspace servers)
- **Instance Class**: `db.t3.micro` or larger depending on expected load
- **Storage**: 100 GB initial (with automatic scaling enabled)
- **Multi-AZ**: Enable for production deployments
- **VPC**: Your ZenML VPC
- **Subnet Group**: Create a DB subnet group with your private subnets
- **Security Group**: RDS security group created above
- **Backups**: 30 days retention minimum
- **Logs**: Enable error, general, and slowquery logs to CloudWatch

**After creation:**
1. Note the database endpoint (hostname)
2. Create the initial database: `zenml_hybrid`
3. Create a database user with full permissions on the database

## Step 3: Store Secrets in AWS Secrets Manager

Store your Pro credentials securely:

1. **OAuth2 Client Secret**
   - Secret name: `zenml/pro/oauth2-client-secret`
   - Value: Your `ZENML_SERVER_PRO_OAUTH2_CLIENT_SECRET` from ZenML

2. (Optional) **Database Password**
   - Secret name: `zenml/rds/password`
   - Value: Your RDS database password

Note the ARN of your OAuth2 secret - you'll reference it in the task definition.

## Step 4: Create ECS IAM Roles

Create two IAM roles:

### Task Execution Role

This role allows ECS to pull images and manage logs:
- Attach: `AmazonECSTaskExecutionRolePolicy`
- Add inline policy for Secrets Manager access:
  - Action: `secretsmanager:GetSecretValue`
  - Resource: Your OAuth2 secret ARN
  - Action: `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`
  - Resource: Your CloudWatch log group

### Task Role

This role is for application-level permissions (optional for basic setup):
- Leave empty for now, or add policies if your tasks need to access other AWS services

## Step 5: Create ECS Task Definition

In the AWS Console or using AWS CLI/Terraform, create a task definition with:

**Task Configuration:**
- **Compatibility**: FARGATE
- **CPU**: 512 (0.5 vCPU)
- **Memory**: 1024 MB
- **Network Mode**: awsvpc
- **Execution Role**: Task execution role created above
- **Task Role**: Task role created above

**Container Configuration:**
- **Image**: `715803424590.dkr.ecr.eu-central-1.amazonaws.com/zenml-pro-server:<ZENML_OSS_VERSION>`
- **Port Mapping**: Container port 8000 to port 8000
- **Essential**: Yes

**Environment Variables:**

Set these in the task definition:

| Variable | Value |
|----------|-------|
| `ZENML_SERVER_DEPLOYMENT_TYPE` | `cloud` |
| `ZENML_SERVER_PRO_API_URL` | `https://cloudapi.zenml.io` |
| `ZENML_SERVER_PRO_DASHBOARD_URL` | `https://cloud.zenml.io` |
| `ZENML_SERVER_PRO_ORGANIZATION_ID` | Your organization ID from Step 1 |
| `ZENML_SERVER_PRO_ORGANIZATION_NAME` | Your organization name from Step 1 |
| `ZENML_SERVER_PRO_WORKSPACE_ID` | From ZenML Support |
| `ZENML_SERVER_PRO_WORKSPACE_NAME` | Your workspace name |
| `ZENML_SERVER_PRO_OAUTH2_AUDIENCE` | `https://cloudapi.zenml.io` |
| `ZENML_SERVER_SERVER_URL` | `https://zenml.mycompany.com` |
| `ZENML_DATABASE_URL` | `mysql://user:password@hostname:3306/zenml_hybrid` (MySQL only - PostgreSQL not supported) |
| `ZENML_SERVER_HOSTNAME` | `0.0.0.0` |
| `ZENML_SERVER_PORT` | `8000` |
| `ZENML_LOGGING_LEVEL` | `INFO` |

**Secrets:**

Reference your secret from Secrets Manager:

| Variable | Secret |
|----------|--------|
| `ZENML_SERVER_PRO_OAUTH2_CLIENT_SECRET` | `arn:aws:secretsmanager:region:account:secret:zenml/pro/oauth2-client-secret` |

**Logging:**

Configure CloudWatch logs:
- **Log Group**: `/ecs/zenml-hybrid`
- **Log Stream Prefix**: `ecs`
- **Region**: Your AWS region

## Step 6: Create ECS Cluster and Service

Create an ECS cluster named `zenml-hybrid`.

Then create an ECS service within this cluster:

**Service Configuration:**
- **Cluster**: zenml-hybrid
- **Task Definition**: zenml-hybrid (latest version)
- **Launch Type**: FARGATE
- **Desired Count**: 1 (or more for high availability)
- **Platform Version**: LATEST

**Network Configuration:**
- **VPC**: Your ZenML VPC
- **Subnets**: Your private subnets
- **Security Group**: ECS security group
- **Public IP**: Disabled (tasks don't need public IPs)

**Load Balancing:**
- **Load Balancer Type**: Application Load Balancer
- **Container**: zenml-server
- **Container Port**: 8000
- (Leave the target group selection for the next step)

## Step 7: Set Up Application Load Balancer

Create an Application Load Balancer (ALB):

**Configuration:**
- **Subnets**: Your public subnets
- **Security Group**: ALB security group

### Target Group

Create a target group for your ECS service:

**Health Check Configuration:**
- **Protocol**: HTTP
- **Path**: `/health`
- **Port**: 8000
- **Interval**: 30 seconds
- **Timeout**: 5 seconds
- **Healthy Threshold**: 2
- **Unhealthy Threshold**: 3

### Listeners

Create two listeners on your ALB:

1. **HTTPS Listener (Port 443)**
   - **Certificate**: Your TLS certificate from ACM or imported
   - **Default Action**: Forward to your target group

2. **HTTP Listener (Port 80)**
   - **Default Action**: Redirect to HTTPS (port 443)

## Step 8: Configure DNS

In your DNS provider (Route 53 or external):

1. Create an A record (or CNAME) pointing to your ALB's DNS name
   - **Name**: `zenml.mycompany.com`
   - **Target**: Your ALB's DNS name or IP
   - **Type**: A record (use Alias if in Route 53)

2. Allow time for DNS propagation (typically 5-15 minutes)

## Step 9: Verify the Deployment

1. **Check ECS Service Status**
   - Go to ECS console → Clusters → zenml-hybrid → Services
   - Verify the service shows "Active"
   - Check that desired and running task counts match

2. **Check Task Logs**
   - Go to CloudWatch → Log Groups → `/ecs/zenml-hybrid`
   - View log stream to look for startup messages
   - Verify no critical errors appear

3. **Test HTTPS Access**
   - Visit `https://zenml.mycompany.com` in your browser
   - You should see ZenML Pro login redirecting to cloud.zenml.io

4. **Verify Control Plane Connection**
   - In CloudWatch logs, look for messages indicating successful connection to ZenML Cloud
   - Check for any authentication or SSL errors

## Network & Firewall Requirements

### Outbound Access to ZenML Cloud

Your ECS tasks need HTTPS (port 443) outbound access to:
- `cloudapi.zenml.io` - For control plane authentication

This is enabled by the NAT Gateway and ECS security group configuration.

### Inbound Access from Clients

Clients need HTTPS (port 443) inbound access to:
- `zenml.mycompany.com` - Your ALB endpoint

This is enabled by the ALB and ALB security group configuration.

### Database Access

ECS tasks need TCP access to:
- Your RDS instance on port 3306 (MySQL)

This is enabled by the ECS security group egress rule and RDS security group ingress rule.

## Scaling & High Availability

### Multiple Tasks

For high availability:
1. Update the ECS service's desired count to 2 or more
2. ECS will distribute tasks across availability zones
3. The ALB automatically distributes traffic to all healthy tasks

### Auto Scaling (Optional)

To automatically scale based on CPU or memory usage:
1. Register a scalable target (your ECS service)
2. Create a target tracking scaling policy
3. Set target CPU utilization (e.g., 70%)

## Monitoring & Logging

### CloudWatch Logs

Monitor your deployment:
1. Go to CloudWatch → Log Groups → `/ecs/zenml-hybrid`
2. Set up log filters to find errors: filter for `ERROR` or `CRITICAL`
3. Create metric filters if needed

### CloudWatch Alarms

Create alarms for:
- **High CPU Utilization**: Alert when average CPU > 80%
- **Failed Tasks**: Alert when tasks exit unexpectedly
- **Unhealthy Targets**: Alert when ALB marks tasks as unhealthy

### Application Logs

For production deployments:
1. Forward CloudWatch logs to your centralized logging system (ELK, Datadog, etc.)
2. Set up alerts for authentication failures to ZenML Cloud
3. Monitor database connection errors

## Database Maintenance

### Backups

Automated backups are configured, but:
1. Verify backup retention is set to at least 30 days
2. Test backup restoration periodically
3. Store backups in a different region for disaster recovery

### Monitoring

Monitor database health:
1. Check RDS Performance Insights for slow queries
2. Review CloudWatch metrics for connection count and CPU
3. Monitor free storage space and create alerts

## (Optional) Enable Snapshot Support / Workload Manager

Pipeline snapshots (running pipelines from the UI) require a workload manager. For ECS deployments, you'll typically use the AWS Kubernetes implementation if you also have a Kubernetes cluster available, or configure settings as appropriate for your infrastructure.

### Prerequisites for Workload Manager

To enable snapshots on ECS-deployed ZenML workspaces:

1. **Kubernetes Cluster Access** - You'll need a Kubernetes cluster where the workload manager can run jobs. This could be:
   - The same EKS cluster as your other infrastructure
   - A separate EKS cluster dedicated to workloads
   - Another Kubernetes distribution in your environment

2. **Container Registry Access** - The workload manager needs access to your container registry to:
   - Pull base ZenML images
   - Push/pull runner images (if building them)

3. **Storage Access** - For AWS implementation:
   - S3 bucket for logs storage
   - IAM permissions to read/write to the bucket

### Configuration Options

**Option A: AWS Kubernetes Workload Manager (Recommended for ECS)**

If you have an EKS cluster or other Kubernetes cluster available:

1. Create a dedicated namespace:
   ```
   kubectl create namespace zenml-workload-manager
   kubectl -n zenml-workload-manager create serviceaccount zenml-runner
   ```

2. Add these environment variables to your ECS task definition:

   | Variable | Value |
   |----------|-------|
   | `ZENML_SERVER_WORKLOAD_MANAGER_IMPLEMENTATION_SOURCE` | `zenml_cloud_plugins.aws_kubernetes_workload_manager.AWSKubernetesWorkloadManager` |
   | `ZENML_KUBERNETES_WORKLOAD_MANAGER_NAMESPACE` | `zenml-workload-manager` |
   | `ZENML_KUBERNETES_WORKLOAD_MANAGER_SERVICE_ACCOUNT` | `zenml-runner` |
   | `ZENML_KUBERNETES_WORKLOAD_MANAGER_BUILD_RUNNER_IMAGE` | `true` |
   | `ZENML_KUBERNETES_WORKLOAD_MANAGER_DOCKER_REGISTRY` | Your ECR registry URI |
   | `ZENML_KUBERNETES_WORKLOAD_MANAGER_ENABLE_EXTERNAL_LOGS` | `true` |
   | `ZENML_AWS_KUBERNETES_WORKLOAD_MANAGER_BUCKET` | Your S3 bucket for logs |
   | `ZENML_AWS_KUBERNETES_WORKLOAD_MANAGER_REGION` | Your AWS region |
   | `ZENML_SERVER_MAX_CONCURRENT_TEMPLATE_RUNS` | `2` (or higher) |
   | `ZENML_KUBERNETES_WORKLOAD_MANAGER_POD_RESOURCES` | `{"requests": {"cpu": "500m", "memory": "512Mi"}, "limits": {"cpu": "2000m", "memory": "2Gi"}}` |

3. Ensure the ECS task has permissions to access:
   - The Kubernetes cluster (kubeconfig/IAM role)
   - Your ECR registry
   - Your S3 bucket for logs

**Option B: Kubernetes-based (Simpler Alternative)**

If you prefer a basic setup without AWS-specific features:

Add these environment variables to your ECS task definition:

| Variable | Value |
|----------|-------|
| `ZENML_SERVER_WORKLOAD_MANAGER_IMPLEMENTATION_SOURCE` | `zenml_cloud_plugins.kubernetes_workload_manager.KubernetesWorkloadManager` |
| `ZENML_KUBERNETES_WORKLOAD_MANAGER_NAMESPACE` | `zenml-workload-manager` |
| `ZENML_KUBERNETES_WORKLOAD_MANAGER_SERVICE_ACCOUNT` | `zenml-runner` |
| `ZENML_KUBERNETES_WORKLOAD_MANAGER_RUNNER_IMAGE` | Your prebuilt ZenML image URI |

### Updating Task Definition

After configuring the workload manager environment variables:

1. Create a new task definition revision with the updated environment variables
2. Update your ECS service to use the new task definition
3. ECS will gradually replace running tasks with the new version
4. Monitor CloudWatch logs to verify the workload manager is operational

## Troubleshooting

### Task Won't Start

Check ECS task logs in CloudWatch:
1. Go to `/ecs/zenml-hybrid` log group
2. Look for error messages about image pull failures or environment variable issues
3. Verify IAM execution role has correct permissions

### Database Connection Failed

1. Verify database is running and accessible
2. Check ECS security group allows outbound to RDS security group
3. Verify `ZENML_DATABASE_URL` has correct hostname, port, and credentials
4. Test connectivity from an ECS task using a MySQL client

### Can't Reach Server via HTTPS

1. Verify ALB is in "Active" state
2. Check ALB target group - tasks should show "Healthy"
3. Verify TLS certificate is valid for your domain
4. Check DNS resolution: `nslookup zenml.mycompany.com`

### Control Plane Connection Issues

Check CloudWatch logs for:
1. OAuth2 authentication errors - verify `ZENML_SERVER_PRO_OAUTH2_CLIENT_SECRET` is correct
2. Network connectivity errors - verify NAT Gateway is operational
3. Certificate validation errors - verify outbound HTTPS to cloudapi.zenml.io works

## Updating the Deployment

### Update Configuration

1. Modify environment variables in the task definition
2. Create a new task definition revision
3. Update the ECS service to use the new task definition
4. ECS will gradually replace old tasks with new ones

### Upgrade ZenML Version

1. Update the container image in the task definition
2. Create a new task definition revision
3. Update the ECS service
4. Monitor CloudWatch logs during the update

## Cleanup

To remove the deployment:

1. **Delete ECS Service**
   - Go to ECS → Clusters → zenml-hybrid → Services
   - Delete the zenml-server service
   - Set desired count to 0 first

2. **Delete ECS Cluster**
   - Delete the cluster once service is removed

3. **Delete ALB**
   - Go to EC2 → Load Balancers
   - Delete the ALB and associated target groups

4. **Delete RDS Instance**
   - Go to RDS → Databases
   - Delete the zenml-hybrid-db instance
   - Skip final snapshot if you don't need a backup

5. **Delete VPC and Related Resources**
   - Delete NAT Gateway (releases Elastic IP)
   - Delete subnets, route tables, security groups
   - Delete VPC

6. **Clean Up Secrets**
   - Go to Secrets Manager
   - Delete zenml/pro/oauth2-client-secret

## Next Steps

- [Configure your organization in ZenML Cloud](https://cloud.zenml.io)
- [Set up users and teams](organization.md)
- [Configure stacks and service connectors](https://docs.zenml.io/stacks)
- [Run your first pipeline](https://github.com/zenml-io/zenml/tree/main/examples/quickstart)

## Related Documentation

- [Hybrid Deployment Overview](hybrid-deployment.md)
- [Self-hosted Deployment Guide](self-hosted.md)
- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [AWS RDS Documentation](https://docs.aws.amazon.com/rds/)
