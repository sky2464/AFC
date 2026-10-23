# Architecture

The living picture of how this project is built. Update it when structure changes.
Never put secrets, keys or passwords here; name where they live instead.

## 1. Goal

What the architecture must make possible, in two or three lines.

## 2. Quality attributes

The qualities that matter most (e.g. simple to run, secure by default, fast to change) and how each
is checked.

## 3. Diagrams

### 3.1 Context

Who and what the system talks to.

### 3.2 Containers

The running pieces (apps, services, databases) and how they connect.

### 3.3 Components

The main modules inside each container.

## 4. Containers and components

| Name | Responsibility | Talks to |
|---|---|---|

## 5. Data flow

How data moves through the system, and what kind of data it is (public, internal, personal).

## 6. Deployment

Where it runs, how it gets there, and what configuration it needs.

## 7. Security

Sign-in and permissions, where secrets live, trust boundaries, and the threat checks made.

## 8. Observability

Logs, metrics and alerts, and what is kept out of logs.

## 9. Decision links

Links to entries in `decisions.md` that shaped this architecture.

## 10. Maintenance rules

Files stay under 500 lines; boundaries stay as drawn here; big changes get a dated decision.
