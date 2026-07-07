# Other Laptop — Remaining Fixes

These steps need to be done on the **other laptop** (the one with SSH access configured and the scripture.db).

## 1. Accept the new host key

```bash
ssh-keyscan -H 40.160.241.74 >> ~/.ssh/known_hosts
```

## 2. Sync the database to the server

The `data/processed/scripture.db` is gitignored and only exists on this machine. Copy it to the server:

```bash
rsync -avz /path/to/ScriptureEngine/data/processed/ scripture.db root@40.160.241.74:/var/www/scripture/data/processed/
```

Or if the server uses `ubuntu` user:

```bash
rsync -avz /path/to/ScriptureEngine/data/processed/scripture.db ubuntu@40.160.241.74:/var/www/scripture/data/processed/
```

## 3. Restart the API server

```bash
ssh ubuntu@40.160.241.74 'sudo systemctl restart scripture-api'
```

## 4. Create `.env` with API key (if not present)

```bash
ssh ubuntu@40.160.241.74 'sudo tee /var/www/scripture/.env'
# Then paste: DEEPSEEK_API_KEY="sk-..."
# Ctrl+D to save
```

## 5. Verify

```bash
curl https://scriptureengine.org/api/v1/health
```
