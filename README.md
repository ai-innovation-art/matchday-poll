# Match Day Poll

A hands-on Kubernetes project. You build and operate a small live-voting system for one busy evening: replicas, autoscaling, releases and rollbacks, failures, and security.

It assumes you already know Kubernetes basics. The guide tells you what to build and how to check it; you write the manifests.

## The system

```
browser -> ingress -> frontend (2 replicas) -> backend (3 replicas) -> redis    (live totals)
                                                                    -> postgres (every vote, on a volume)
```

| Part | Image | Workload |
|---|---|---|
| frontend | built from `app/frontend/Dockerfile` | Deployment |
| backend | built from `app/backend/Dockerfile` | Deployment |
| database | `postgres:16-alpine` | StatefulSet |
| cache | `redis:7-alpine` | Deployment |

No container registry is needed. You build the two images locally and load them into a `kind` cluster.

## Read the guide

The guide is a set of web pages in [`docs/`](docs/). Open [`docs/index.html`](docs/index.html) in a browser, or read it online if GitHub Pages is enabled for this repository (Settings, Pages, deploy from branch `main`, folder `/docs`).

Each mission has a goal, a check, and optional hints and a full solution. Try it yourself first.

## What is here

```
app/frontend/   nginx and the poll page (Dockerfile ready)
app/backend/    the API and a small tools script (Dockerfile ready)
docs/           the guide
k8s/            empty: your manifests go here
scripts/        empty: your scripts go here
```

## You need

Docker, [kind](https://kind.sigs.k8s.io/), `kubectl`, `bash` and `curl`. About 6 GB of free memory.

## Start

```
docker build -t poll-backend:1.0 app/backend
docker build -t poll-frontend:1.0 app/frontend
```

Then follow [Act 0](docs/00-setup.html).
