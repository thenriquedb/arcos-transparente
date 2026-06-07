## ADDED Requirements

### Requirement: Repository defines an official Docker runtime for the application
The system MUST provide an official Docker-based runtime for this repository that
packages the application code, Python dependencies, and the Streamlit web
entrypoint into a reproducible image.

#### Scenario: Image build succeeds from repository state
- **WHEN** an operator builds the official Docker image from the repository root
- **THEN** the build includes the application source code and required Python dependencies
- **AND** the resulting image can start the citizen-facing web interface without requiring Python or `uv` on the host machine

#### Scenario: Container starts the Streamlit interface by default
- **WHEN** an operator starts the container without overriding its command
- **THEN** the container runs the Streamlit chatbot interface as its default process
- **AND** the web service listens on all interfaces and a configurable container port suitable for Docker deployment

### Requirement: Docker runtime preserves local state through explicit persistent storage
The system MUST define explicit persistent storage for mutable runtime artifacts
created by the current local architecture, including the SQLite database and the
local vector-store persistence.

#### Scenario: SQLite runtime path is redirected to mounted persistent storage
- **WHEN** the application runs through the official Docker workflow
- **THEN** `DATABASE_URL` resolves to a SQLite file path inside the mounted runtime storage
- **AND** the container does not depend on writing the primary database into the versioned source tree

#### Scenario: Vector-store persistence survives container recreation
- **WHEN** the application generates or reuses the local RAG index in the Docker workflow
- **THEN** the vector-store persist directory points to mounted runtime storage
- **AND** recreating the container with the same persistent volume preserves the previously generated index artifacts

### Requirement: Docker operations reuse the existing CLI contract through the same image
The system MUST support the repository's existing operational commands through
the same official Docker image used for the web interface.

#### Scenario: Operator initializes the database through the containerized CLI
- **WHEN** an operator runs the documented Docker command for `db init`
- **THEN** the container executes the existing project CLI to apply database migrations
- **AND** the resulting database artifacts are written to the configured persistent runtime storage

#### Scenario: Operator runs import and RAG indexing through the same image
- **WHEN** an operator runs the documented Docker commands for `importar` and `rag index`
- **THEN** the commands execute through the same official application image
- **AND** the imported SQLite data and generated RAG artifacts remain available to later web sessions that reuse the same persistent storage

### Requirement: Docker workflow is documented with its operational constraints
The repository MUST document the official Docker workflow, including the current
single-instance stateful constraint imposed by the local SQLite-based
architecture.

#### Scenario: Documentation explains how to build and run with Docker
- **WHEN** a contributor follows the Docker section in the repository documentation
- **THEN** the documentation shows the canonical steps to build the image, provide the required environment variables, start the web interface, and run the containerized maintenance commands
- **AND** the instructions identify which storage path or volume must persist between runs

#### Scenario: Documentation warns about current single-instance behavior
- **WHEN** an operator reads the Docker guidance for deployment
- **THEN** the documentation states that the official Docker workflow is intended for a single stateful instance in the current phase
- **AND** it does not imply horizontal scaling support without additional architectural changes
