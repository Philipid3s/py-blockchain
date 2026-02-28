# PyBlockchain

A minimal **Proof of Concept** built in Python that demonstrates how blockchain technology works as a decentralized content-sharing platform. The entire blockchain core is under 100 lines — intentionally small so every concept is easy to follow and inspect.

---

## What it does

- Write a **message** → it becomes a pending **transaction**
- **Mine** pending transactions → they are sealed into a **block** and appended to the chain
- All blocks are linked by **SHA-256 hashes** — altering any block breaks the chain
- Data persists across restarts via a local **SQLite** database

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Web Framework | Flask |
| Database | SQLite (local file, via built-in `sqlite3`) |
| Hash Function | SHA-256 |
| Consensus | Proof of Work (difficulty = 2 leading zeros) |
| UI | Custom dark-theme CSS, no framework |
| Container | Docker |

---

## Getting Started

### Run locally (Python)

```bash
git clone https://github.com/your-username/py-blockchain.git
cd py-blockchain
pip install -r requirements.txt
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.
The `blockchain.db` file is created automatically on first run.

### Run locally (Docker)

```bash
docker pull philipid3s/py-blockchain:latest
docker run -p 8000:8000 -v blockchain_data:/data philipid3s/py-blockchain:latest
```

Open [http://localhost:8000](http://localhost:8000).

---

## How it works

### Blockchain structure

Each **block** contains:
- `index` — position in the chain
- `transactions` — list of posts included in the block
- `timestamp` — when it was mined
- `previous_hash` — SHA-256 hash of the preceding block (forms the chain)
- `nonce` — the value found by Proof of Work
- `hash` — SHA-256 hash of all the above

```
[Genesis Block] → [Block #1] → [Block #2] → ···
  prev: "0"        prev: 00a1…   prev: 00b7…
  hash: 00a1…      hash: 00b7…   hash: 00e9…
```

### Proof of Work

Mining finds a `nonce` such that:

```
SHA-256(index + transactions + timestamp + prev_hash + nonce)
  starts with "00..."
```

This is expensive to compute, instant to verify. Difficulty is set to `2` (two leading zeros).

### Step-by-step flow

1. **Create a transaction** — fill in the form. The post goes into the pending pool via `POST /new_transaction`.
2. **Mine a block** — click *Request Mining*. The server bundles all pending transactions, runs PoW, and appends the block to the chain.
3. **Explore the chain** — mined posts appear in the feed. Use `/chain` to inspect the raw JSON.

---

## Project Structure

```
py-blockchain/
├── app.py                        # Flask routes + database helpers
├── blockchain.py                 # BlockChain class (PoW, mining, chain)
├── block.py                      # Block class (SHA-256 hashing)
├── templates/
│   ├── base.html                 # Layout, CSS, guide modal
│   └── index.html                # Main page (form, feed)
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .github/
│   └── workflows/
│       └── ci.yml                # CI lint + Docker Hub push
├── requirements.txt
├── Procfile
└── .gitignore
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Main UI — loads and displays the chain |
| `POST` | `/new_transaction` | Add a transaction to the pending pool |
| `POST` | `/submit` | Form handler — wraps `/new_transaction` |
| `GET` | `/mine` | Run PoW, seal a block, append to chain |
| `GET` | `/chain` | Return full blockchain as JSON |
| `GET` | `/pending_tx` | Return unconfirmed transactions as JSON |
| `POST` | `/add_block` | Accept an externally mined block (node sync) |
| `GET` | `/reset` | Clear the entire chain and database |

---

## Deployment — Hostinger VPS via Docker Hub

The CI pipeline automatically builds and pushes the image to
**[philipid3s/py-blockchain](https://hub.docker.com/r/philipid3s/py-blockchain)**
on every push to `master`.

### CI/CD flow

```
git push master
    └─▶ GitHub Actions: lint checks
            └─▶ docker build
                    └─▶ docker push philipid3s/py-blockchain:latest
                                └─▶ Pull & restart on VPS (manual or webhook)
```

### 1 — Configure GitHub Secrets

In your GitHub repo → **Settings → Secrets and variables → Actions**, add:

| Secret | Value |
|---|---|
| `DOCKERHUB_USERNAME` | `philipid3s` |
| `DOCKERHUB_TOKEN` | Your Docker Hub access token (not your password) |

Generate a token at [hub.docker.com → Account Settings → Security](https://hub.docker.com/settings/security).

### 2 — First-time VPS setup

SSH into your Hostinger VPS and install Docker:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # allow running docker without sudo (re-login after)
```

Copy `docker-compose.yml` to the VPS (or clone the repo):

```bash
scp docker-compose.yml user@your-vps-ip:~/py-blockchain/
# or
git clone https://github.com/your-username/py-blockchain.git && cd py-blockchain
```

### 3 — Start the app

```bash
cd ~/py-blockchain
docker compose pull          # get the latest image from Docker Hub
docker compose up -d         # start in background
```

The app is now running on **port 8000**. The SQLite database is stored in a Docker volume (`blockchain_data`) and survives container restarts and image updates.

### 4 — Update after a new push

After GitHub Actions pushes a new image, run on the VPS:

```bash
docker compose pull && docker compose up -d
```

> **Tip:** Automate this with a simple cron job or a Docker Hub webhook pointing to a lightweight update script on your VPS.

### 5 — (Optional) Reverse proxy with Nginx

To serve on port 80/443, install Nginx and add a site config:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Then get a free SSL certificate:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `BASE_URL` | `http://localhost:8000` | URL the app uses to self-call for `/submit` |
| `DB_PATH` | `blockchain.db` | Path to the SQLite database file |

---

## Known limitations (by design)

This is a PoC — not production-ready:

- No authentication or access control on `/reset`
- Single-node only (no real peer-to-peer networking)
- PoW difficulty (`2`) is low — mines in milliseconds
- No chain integrity validation on startup
- `/add_block` endpoint has a syntax bug (see issue tracker)
- Single gunicorn worker required due to shared in-memory state

---

## Inspired by

[Build a blockchain app in Python — IBM Developer](https://www.ibm.com/developerworks/cloud/library/cl-develop-blockchain-app-in-python/index.html)
