# DynamoDB Multi-Table Design

## Table Structure

### 1. Users Table
**Purpose**: Store user authentication and profile data

| Attribute | Type | Key | Description |
|-----------|------|-----|-------------|
| user_id | String | PK | Primary key (Google sub ID) |
| email | String | GSI1-PK | User email address |
| name | String | - | Full name |
| google_id | String | - | Google OAuth ID (same as user_id) |
| created_at | String | - | ISO timestamp |
| last_login | String | - | ISO timestamp |

**Indexes**:
- GSI1: email (PK) - for email-based lookups

### 2. SecurityAssessments Table
**Purpose**: Store security assessment metadata

| Attribute | Type | Key | Description |
|-----------|------|-----|-------------|
| assessment_id | String | PK | Primary key (UUID) |
| collaborator_ids | StringSet | GSI1-PK | Set of all user IDs with access (including creator) |
| product_name | String | - | Product being assessed |
| product_description | String | - | Detailed description |
| status | String | - | draft/in_progress/completed |
| created_at | String | GSI1-SK | ISO timestamp |
| updated_at | String | - | ISO timestamp |

**Indexes**:
- GSI1: collaborator_ids (PK), created_at (SK) - for user's accessible assessments ordered by date

### 3. Controls Table
**Purpose**: Store NIST 800-53 controls within assessments

| Attribute | Type | Key | Description |
|-----------|------|-----|-------------|
| control_id | String | PK | Primary key (UUID) |
| assessment_id | String | GSI1-PK | Parent assessment |
| nist_control_id | String | GSI1-SK | NIST control identifier (e.g., AC-1) |
| control_title | String | - | Control title |
| control_description | String | - | Control description |
| implementation_status | String | - | not_started/partial/implemented |
| created_at | String | - | ISO timestamp |
| updated_at | String | - | ISO timestamp |

**Indexes**:
- GSI1: assessment_id (PK), nist_control_id (SK) - for controls within assessment

### 4. Evidence Table
**Purpose**: Store evidence documents for controls

| Attribute | Type | Key | Description |
|-----------|------|-----|-------------|
| evidence_id | String | PK | Primary key (UUID) |
| control_id | String | GSI1-PK | Parent control |
| title | String | - | Evidence title |
| description | String | - | Evidence description |
| evidence_type | String | - | document/screenshot/policy/etc |
| file_url | String | - | S3 URL if file upload |
| created_at | String | GSI1-SK | ISO timestamp |
| updated_at | String | - | ISO timestamp |

**Indexes**:
- GSI1: control_id (PK), created_at (SK) - for evidence within control

## Access Patterns

### Primary Patterns
1. **Get user by Google ID**: Users.user_id = google_id
2. **Get user by email**: Users.GSI1 where email = ?
3. **Get user's accessible assessments**: SecurityAssessments.GSI1 where collaborator_ids = user_id
4. **Check user access to assessment**: Get assessment by PK, check if user_id in collaborator_ids
5. **Get assessment controls**: Controls.GSI1 where assessment_id = ?
6. **Get control evidence**: Evidence.GSI1 where control_id = ?

### Secondary Patterns
7. **Get all assessments with status**: Query with filter on status
8. **Get controls by NIST ID**: Query with filter on nist_control_id
9. **Get recent evidence**: Evidence.GSI1 with date range

## Benefits of Multi-Table Design

1. **Clear separation of concerns**: Each entity type has its own table
2. **Independent scaling**: Tables can be sized based on usage patterns
3. **Simpler queries**: No complex composite keys or entity type discrimination
4. **Better permissions**: Can set IAM policies per table
5. **Easier backup/restore**: Can backup entities independently
6. **Team ownership**: Different teams can own different tables

## Performance Considerations

- Use batch operations for related data (e.g., batch get controls for assessment)
- Consider connection pooling for multiple table access
- Use consistent reads only when necessary
- Implement caching for frequently accessed user data