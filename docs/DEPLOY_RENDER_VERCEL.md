# Deploying on Render and Vercel

The web app runs on Vercel. The API, the report worker, the OCR service and
Redis run on Render, defined in [`render.yaml`](../render.yaml). MongoDB runs on
MongoDB Atlas, and the AI model is Groq's API. For the single-server Docker
setup, see [DEPLOYMENT.md](DEPLOYMENT.md).

> **Use test data only on this setup.** Vercel's free Hobby plan is for
> non-commercial use, and free AI tiers have terms that may not suit health
> data. Section 9 lists what to change before real patients use it.

## 1. What runs where

| Part | Where | Plan | Cost |
|---|---|---|---|
| Web app (Next.js) | Vercel | Hobby | Free |
| API | Render web service `nutrimed-api` | Free: sleeps after 15 minutes idle | Free |
| Report worker (Celery) | Render background worker `nutrimed-worker` | Starter (0.5 CPU, 512 MB) | About $7/month |
| OCR service | Render private service `nutrimed-ocr` | Starter | About $7/month |
| Redis | Render Key Value `nutrimed-redis` | Free: 25 MB, not saved to disk | Free |
| Database and uploaded reports | MongoDB Atlas | M0: 512 MB | Free |
| AI model | Groq | Free tier, rate-limited | Free |

Render has no free plan for background workers or private services, so this
setup costs about $14 a month. See [render.com/pricing](https://render.com/pricing).

Browsers load the app from Vercel and call the API on Render directly over
HTTPS. The OCR service has no public address; only the API and the worker can
reach it, over Render's private network.

## 2. Before you start

- **Merge the work into `main`**, or pick your branch when you create the
  Blueprint (section 5) and the Vercel project (section 6).
- You need accounts on GitHub (with access to the repository), Render,
  Vercel, MongoDB Atlas and Groq.
- **Choose the addresses up front, because each side needs the other's:**
  - The API will be `https://nutrimed-api.onrender.com`. Render adds a suffix
    if that name is taken.
  - The app will be `https://<project-name>.vercel.app`.

## 3. MongoDB Atlas

1. Create a free **M0** cluster. Choose the region closest to Singapore that
   the free tier offers, since the Render services run in Singapore.
2. **Database Access:** add a user with a generated password of letters and
   digits only (other characters must be URL-encoded in the connection
   string), with read and write access.
3. **Network Access:** allow `0.0.0.0/0` for now. Section 5 replaces it with
   Render's addresses.
4. **Connect, then Drivers:** copy the `mongodb+srv://...` string and put the
   password in it. The database name is set separately (`MONGO_DB_NAME=nutrimed`).

## 4. Groq

Create an API key at [console.groq.com](https://console.groq.com). Paste it
only into Render; never put it in the repository or a chat.

## 5. Render

1. In the Dashboard, choose **New**, then **Blueprint**, and connect the
   repository and branch. Render reads `render.yaml` and lists four services
   and the `nutrimed-shared` environment group.
2. Enter the values it asks for. All of them are on `nutrimed-api`; the
   worker copies `MONGO_URI` and `LLM_API_KEY` from it.

   | Variable | Value |
   |---|---|
   | `MONGO_URI` | The Atlas connection string |
   | `LLM_API_KEY` | Your Groq key |
   | `ALLOWED_ORIGINS` | `["https://<project-name>.vercel.app"]`, a JSON list |
   | `FRONTEND_URL` | `https://<project-name>.vercel.app` |

3. Apply. Render asks for a card for the two paid services. The first builds
   take several minutes.
4. **Save the generated secrets.** Under **Environment Groups**, open
   `nutrimed-shared` and copy `JWT_SECRET` and `AES_KEY` into a password
   manager. **Never change `AES_KEY`:** uploaded reports are encrypted with it.
5. **Lock down Atlas.** Open any of the services, choose **Connect**, then
   **Outbound**, and add those address ranges under Atlas Network Access.
   Then delete `0.0.0.0/0`.
6. **Check the API:**
   - `https://<api>/health` should return `{"status":"ok",...}`.
   - `https://<api>/health/ready` should show `mongodb`, `llm` and `ocr` as ok.

**Password-reset email (optional).** On `nutrimed-api`, open **Environment**
and add `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` and `SMTP_FROM`.

> **Use `SMTP_PORT=2525`:** Render's free plan blocks outgoing ports 25, 465
> and 587. Brevo, SendGrid, Mailgun and Postmark accept 2525. Alternatively,
> move the API to the Starter plan.

Variables you add in the Dashboard survive Blueprint syncs. Values defined in
`render.yaml` are reset to the file's value on each sync, so change those in
the file.

## 6. Vercel

1. Choose **Add New**, then **Project**, and import the repository.
2. Set **Root Directory** to `frontend`. Vercel detects Next.js.
3. Under **Environment Variables**, add `NEXT_PUBLIC_API_URL` =
   `https://<api>.onrender.com/api/v1` for Production and Preview.
   - The build fails with a clear message if the variable is missing or isn't `https://`.
   - The value is compiled into the app, so redeploy after changing it.
4. Deploy. If the project's address differs from the one you entered in
   section 5, update `ALLOWED_ORIGINS` and `FRONTEND_URL` on `nutrimed-api`.

[`next.config.ts`](../frontend/next.config.ts) sends the same security headers
as the Docker setup's nginx, with the API's address allowed in the CSP. Vercel
adds HSTS itself.

**Preview deployments** (pushes to other branches) get their own addresses,
which the API refuses until you allow them. On `nutrimed-api`, add
`ALLOWED_ORIGIN_REGEX` = `^https://nutrimed-[a-z0-9-]+-<team-slug>\.vercel\.app$`,
copying `<team-slug>` from the end of a preview's address. Previews use the
production API and database.

## 7. Admin account and visitor addresses

**Create the admin account:**

1. Register at `https://<project-name>.vercel.app/register`.
2. In Atlas, open **Browse Collections**, then `nutrimed`, then `users`.
   Set your user's `role` to `"admin"`. **Never run the seed script in
   production.**
3. Sign out and in again.

**Check the visitor address.** The rate limiter, and its protection of the
sign-in page, depends on the API seeing each visitor's real address.

- Render doesn't document which header carries it. `render.yaml` uses
  `CF-Connecting-IP`, which Render's Cloudflare edge is reported to set.
- To check it, open the browser console on the signed-in app and run:

  ```js
  const r = await fetch("https://<api>.onrender.com/api/v1/admin/client-ip", {
    headers: {
      Authorization: "Bearer " + localStorage.getItem("token"),
      "CF-Connecting-IP": "203.0.113.7",
      "X-Forwarded-For": "203.0.113.7",
    },
  });
  console.log(await r.json());
  ```

**Correct result:** `client_ip` is your own public address, not `203.0.113.7`,
and `scheme` is `https`. Otherwise, use the `headers` part of the response:

| What you see | Change in `render.yaml` on `nutrimed-api` |
|---|---|
| `client_ip` is `203.0.113.7` | A client can choose its address. Set `CLIENT_IP_HEADER` to `True-Client-IP` if that header shows your real address; otherwise use the next two rows. |
| `cf-connecting-ip` is empty, and your address is last in `x-forwarded-for` | `CLIENT_IP_HEADER` = `X-Forwarded-For` |
| Your address is second to last in `x-forwarded-for` | Same, plus `CLIENT_IP_HOPS` = `2` |

Push the change, wait for the deploy, and run the check again.

## 8. Updates and rollback

**Deploys:**

- **Render** deploys a service when a push to the branch changes its files
  and the GitHub checks pass (`autoDeployTrigger: checksPass`).
- **Vercel** deploys every push.
- `.github/workflows/cd.yml` is for the Docker server. It runs only on `v*`
  tags or manually, so it doesn't interfere.

**Rollback:**

- **Render:** open the service's Events and choose **Rollback** on an
  earlier deploy.
- **Vercel:** open **Deployments** and choose **Instant Rollback**.

## 9. Limits of the free setup

| Limit | What it means | For real use |
|---|---|---|
| The API sleeps | The first request after 15 idle minutes takes about a minute | Set `plan: starter` for `nutrimed-api` (about $7/month) |
| Redis isn't saved | A restart drops queued jobs; those reports must be analysed again | A paid Key Value plan |
| Atlas M0 | 512 MB holds a few hundred reports, and **there are no automatic backups** | A paid tier with backups. Until then, back up regularly with `mongodump --uri "<MONGO_URI>" --db nutrimed --archive=nutrimed-$(date +%F).gz --gzip` |
| Groq free tier | When rate-limited, plans fall back to templates; `/health/ready` reports the share | A paid plan whose terms rule out training on, or keeping, your data |
| Vercel Hobby | Non-commercial use only | Vercel Pro |
| Sign-in rate limit | No nginx, so only the API's own limit applies: 60 requests a minute per visitor (the Docker setup also limits sign-in to 20 a minute) | Keep in mind when reviewing security |
| Region | Render runs in Singapore; Atlas in the region you chose | Check your data-residency obligations |

The API's interactive docs (`/docs`) are turned off whenever `DEBUG` is off.

## 10. Checklist

- [ ] Atlas M0 cluster, database user, connection string
- [ ] Groq key, entered only on Render
- [ ] Blueprint applied; `JWT_SECRET` and `AES_KEY` saved in a password manager
- [ ] Atlas Network Access limited to Render's outbound addresses
- [ ] `/health/ready` shows `mongodb`, `llm` and `ocr` as ok
- [ ] Vercel project with Root Directory `frontend` and `NEXT_PUBLIC_API_URL`
- [ ] `ALLOWED_ORIGINS` and `FRONTEND_URL` match the Vercel address
- [ ] Admin account promoted in Atlas (seed script **not** run)
- [ ] Visitor-address check (section 7) passes
- [ ] SMTP on port 2525, if you want password-reset emails
- [ ] Test data only until section 9 is addressed
