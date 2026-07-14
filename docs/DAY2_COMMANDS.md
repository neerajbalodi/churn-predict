# Day 2 — Command Reference

Every command you'll run on Day 2, in order, with explanations.

---

## Prerequisites Check

### 1. Verify Docker is running

```bash
docker --version
```

What it does: Confirms Docker CLI is installed and ready. Jenkins itself will run as a Docker container, and it will build Docker images inside the pipeline.

---

### 2. Verify Git is configured

```bash
git config --get user.name
git config --get user.email
```

What it does: Confirms Git knows who you are. Commits need a name and email. If empty, set them:

```bash
git config --global user.name "Your Name"
git config --global user.email "your@email.com"
```

---

### 3. Verify your repo has a remote

```bash
git remote -v
```

What it does: Shows the remote repository URL (GitHub, GitLab, etc.) that `git push` sends code to. Jenkins will pull from this URL. If no remote exists:

```bash
git remote add origin <your-repo-url>
```

---

## Starting Jenkins

### 4. Start Jenkins as a Docker container

```bash
docker run -d --name jenkins \
  -p 8080:8080 -p 50000:50000 \
  -v jenkins_home:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  jenkins/jenkins:lts
```

What it does:
- `docker run -d` — run in background (detached mode)
- `--name jenkins` — name the container "jenkins" for easy reference
- `-p 8080:8080` — Jenkins web UI on port 8080
- `-p 50000:50000` — Jenkins agent communication port
- `-v jenkins_home:/var/jenkins_home` — persist Jenkins data in a Docker volume (survives container restarts)
- `-v /var/run/docker.sock:/var/run/docker.sock` — lets Jenkins run Docker commands on the host (needed for `docker build` and `docker push` inside the pipeline)
- `jenkins/jenkins:lts` — official Jenkins Long-Term Support image

First run pulls the image (~300MB). Takes 1-2 minutes.

---

### 5. Verify Jenkins is running

```bash
docker ps | grep jenkins
```

What it does: Lists running containers and filters for Jenkins. Should show one container named "jenkins" with status "Up."

---

### 6. Get the initial admin password

```bash
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

What it does:
- `docker exec jenkins` — run a command inside the running Jenkins container
- `cat .../initialAdminPassword` — prints the one-time setup password

Copy this password — you'll need it in the next step.

---

### 7. Open Jenkins in the browser

```bash
open http://localhost:8080
```

On Linux:

```bash
xdg-open http://localhost:8080
```

What it does: Opens the Jenkins setup wizard. Paste the admin password from step 6.

---

## Jenkins Setup (Browser)

Steps 8-12 are done in the Jenkins web UI, not the terminal.

### 8. Unlock Jenkins

Paste the admin password from step 6 into the "Administrator password" field. Click **Continue**.

---

### 9. Install plugins

Click **Install suggested plugins**. Wait for all plugins to install (~2-3 minutes). This installs Git, Pipeline, and other essential plugins.

---

### 10. Create admin user

Fill in:
- Username: `admin` (or your choice)
- Password: choose a password
- Full name: your name
- Email: your email

Click **Save and Continue**. Then **Save and Finish**. Then **Start using Jenkins**.

---

### 11. Install Docker Pipeline plugin

1. Go to **Manage Jenkins** (left sidebar) > **Plugins**
2. Click **Available plugins** tab
3. Search for `Docker Pipeline`
4. Check the box next to it
5. Click **Install**
6. Restart Jenkins if prompted

What it does: Lets Jenkins build and push Docker images inside pipeline stages.

---

### 12. Add Docker Hub credentials

1. Go to **Manage Jenkins** > **Credentials**
2. Click **System** > **Global credentials (unrestricted)**
3. Click **Add Credentials**
4. Fill in:
   - Kind: **Username with password**
   - Scope: **Global**
   - Username: your Docker Hub username
   - Password: your Docker Hub password or access token
   - ID: `registry-credentials`
   - Description: `Docker Hub`
5. Click **Create**

What it does: Stores your Docker Hub login securely inside Jenkins. The Jenkinsfile references this by ID (`registry-credentials`). The actual password is never in your code.

---

## Configure the Jenkinsfile

### 13. Update the image name in Jenkinsfile

Edit `Jenkinsfile` line 13 — replace `REPLACE_ME`:

```bash
sed -i '' 's|REPLACE_ME/churn-api|<your-dockerhub-username>/churn-api|' Jenkinsfile
```

On Linux (without the `''`):

```bash
sed -i 's|REPLACE_ME/churn-api|<your-dockerhub-username>/churn-api|' Jenkinsfile
```

What it does: Replaces the placeholder image name with your actual Docker Hub username. Jenkins will push images to `<your-username>/churn-api:<build-number>`.

Verify the change:

```bash
grep IMAGE Jenkinsfile
```

Expected:

```
IMAGE = "<your-dockerhub-username>/churn-api"
```

---

### 14. Commit and push the Jenkinsfile change

```bash
git add Jenkinsfile
git commit -m "Configure Jenkinsfile with Docker Hub username"
git push
```

What it does: Commits the updated Jenkinsfile and pushes to the remote repository. Jenkins will pull this file to know how to run the pipeline.

---

## Create the Pipeline Job (Browser)

Steps 15-17 are done in the Jenkins web UI.

### 15. Create a new pipeline job

1. From the Jenkins dashboard, click **New Item** (left sidebar)
2. Enter name: `churn-api`
3. Select **Pipeline**
4. Click **OK**

---

### 16. Configure the pipeline source

On the job configuration page, scroll down to the **Pipeline** section:

1. Definition: select **Pipeline script from SCM**
2. SCM: select **Git**
3. Repository URL: paste your Git repo URL
4. Branch Specifier: `*/main` (or `*/master`, whichever your repo uses)
5. Script Path: `Jenkinsfile` (default, leave as-is)
6. Click **Save**

What it does: Tells Jenkins where to find your code and Jenkinsfile. On every build, Jenkins clones the repo and runs the pipeline defined in the Jenkinsfile.

---

### 17. Verify the branch name

If unsure about your branch name:

```bash
git branch
```

What it does: Lists local branches. The one with `*` is your current branch. Use this name in the Jenkins branch specifier.

---

## Run the Pipeline

### 18. Trigger the first build

In Jenkins, click **Build Now** (left sidebar of the churn-api job page).

What it does: Jenkins clones your repo, reads the Jenkinsfile, and executes each stage in order:
1. Setup — creates venv, installs dependencies
2. Train + Gate — runs `python train.py`, checks accuracy
3. Test — runs `pytest -q`
4. Build Image — runs `docker build`
5. Push Image — logs into Docker Hub, pushes the image
6. Deploy to EKS — will fail (no cluster yet, expected)

---

### 19. Watch the Stage View

On the job page, the **Stage View** appears after the build starts. Each stage shows:
- Blue (running)
- Green (passed)
- Red (failed)
- Grey (not run)

Expected for first build (no EKS yet):

```
Setup [green] > Train+Gate [green] > Test [green] > Build [green] > Push [green] > Deploy [red]
```

Deploy to EKS fails because the cluster doesn't exist yet — that's Day 3. Everything else should be green.

---

### 20. View the console output

Click on the build number (e.g., `#1`) > **Console Output**.

What it does: Shows the full log of every command Jenkins ran. Scroll through to see:
- pip install output
- Training output (accuracy, threshold, PASS)
- Test output (4 passed)
- Docker build output
- Docker push output

---

### 21. View a specific stage's log

In the Stage View, click on any green/red box (e.g., "Train + Gate") > **Logs**.

What it does: Shows only the console output for that specific stage. Useful for debugging without scrolling through the entire log.

---

### 22. Check the Train + Gate stage output

Click into the **Train + Gate** stage log. Look for:

```
Churn rate in data : 52.4%
Test accuracy      : 0.879
Accuracy threshold : 0.78
PASS: saved model.joblib
```

What it confirms: The model trained successfully inside the pipeline and passed the quality gate.

---

### 23. Check the Test stage output

Click into the **Test** stage log. Look for:

```
....                                                                     [100%]
4 passed in 1.20s
```

What it confirms: All 4 tests passed — API works, validation works, model behavior is sensible.

---

## Demo: Break the Pipeline

### 24. Raise the accuracy threshold

Edit `train.py` line 24:

```bash
sed -i '' 's/ACCURACY_THRESHOLD = 0.78/ACCURACY_THRESHOLD = 0.99/' train.py
```

On Linux:

```bash
sed -i 's/ACCURACY_THRESHOLD = 0.78/ACCURACY_THRESHOLD = 0.99/' train.py
```

What it does: Changes the quality gate from 0.78 to 0.99. The model's accuracy is 0.879, which is below 0.99, so the gate will fail.

Verify:

```bash
grep ACCURACY_THRESHOLD train.py
```

Expected:

```
ACCURACY_THRESHOLD = 0.99
```

---

### 25. Commit and push the breaking change

```bash
git add train.py
git commit -m "Raise threshold to 0.99 (will fail)"
git push
```

What it does: Pushes code that will cause the pipeline to fail. If Jenkins has a webhook configured, the build triggers automatically. Otherwise, click **Build Now** in Jenkins.

---

### 26. Trigger the build (if no webhook)

In Jenkins, go to the churn-api job and click **Build Now**.

What it does: Starts a new build with the updated threshold.

---

### 27. Watch the pipeline fail

Watch the Stage View. Expected:

```
Setup [green] > Train+Gate [RED] > Test [grey] > Build [grey] > Push [grey] > Deploy [grey]
```

What happened:
- Setup passed — dependencies installed fine
- Train + Gate FAILED — accuracy 0.879 < threshold 0.99
- Test, Build, Push, Deploy — never ran (pipeline stopped)

---

### 28. View the failure details

Click into the **Train + Gate** stage log. Look for:

```
FAIL: accuracy 0.879 < threshold 0.99. Refusing to save a sub-par model.
```

What it confirms: The quality gate works. A sub-par model was caught. No Docker image was built. Nothing was pushed. Nothing was deployed. The bad model never got anywhere near production.

---

### 29. Revert the threshold

```bash
sed -i '' 's/ACCURACY_THRESHOLD = 0.99/ACCURACY_THRESHOLD = 0.78/' train.py
```

On Linux:

```bash
sed -i 's/ACCURACY_THRESHOLD = 0.99/ACCURACY_THRESHOLD = 0.78/' train.py
```

Verify:

```bash
grep ACCURACY_THRESHOLD train.py
```

Expected:

```
ACCURACY_THRESHOLD = 0.78
```

---

### 30. Commit and push the fix

```bash
git add train.py
git commit -m "Revert threshold to 0.78"
git push
```

What it does: Pushes the fix. The next build should pass.

---

### 31. Run the fixed build

Click **Build Now** in Jenkins (or wait for webhook trigger).

Watch the Stage View — all stages go green again (except Deploy to EKS which is expected to fail without the cluster).

---

## Verify the Results

### 32. Check Docker Hub for the pushed image

```bash
open https://hub.docker.com/r/<your-dockerhub-username>/churn-api/tags
```

What it does: Opens your Docker Hub repository page. You should see image tags matching Jenkins build numbers (e.g., `1`, `3` — build `2` failed so no image was pushed for that one).

---

### 33. Pull and run the Jenkins-built image (optional)

```bash
docker pull <your-dockerhub-username>/churn-api:latest
docker run -p 8000:8000 <your-dockerhub-username>/churn-api:latest
```

What it does: Pulls the image that Jenkins built and pushed, and runs it locally. Proves that the pipeline produced a working image.

Test it:

```bash
curl http://localhost:8000/health
```

Expected:

```json
{"status": "ok", "trained_accuracy": 0.879}
```

Stop with Ctrl+C.

---

### 34. View Jenkins build history

In Jenkins, go to the churn-api job page. The build history (left sidebar) shows:

```
#3 — green (reverted threshold, all passed)
#2 — red (threshold 0.99, Train+Gate failed)
#1 — green/partial (first build, Deploy failed - no EKS)
```

What it confirms: Jenkins keeps a history of every build — what passed, what failed, when.

---

## Setting Up Webhooks (Optional)

### 35. Get your Jenkins URL

If Jenkins is accessible from the internet (not just localhost), you can set up automatic triggers.

For local development, you can use a tunnel:

```bash
ngrok http 8080
```

What it does: Creates a public URL that tunnels to your local Jenkins. Copy the `https://xxxx.ngrok.io` URL.

---

### 36. Add webhook in GitHub

1. Go to your GitHub repo > **Settings** > **Webhooks** > **Add webhook**
2. Payload URL: `https://xxxx.ngrok.io/github-webhook/` (trailing slash required)
3. Content type: `application/json`
4. Which events: **Just the push event**
5. Click **Add webhook**

What it does: GitHub sends a POST request to Jenkins every time you push code. Jenkins automatically triggers a new build — no need to click "Build Now."

---

### 37. Test the webhook

Make any small change, commit, and push:

```bash
echo "# webhook test" >> README.md
git add README.md
git commit -m "Test webhook trigger"
git push
```

What it does: Pushes a trivial change. If the webhook is configured correctly, Jenkins will start a new build automatically within seconds.

Check Jenkins — a new build should appear in the build history.

Revert the change:

```bash
git checkout README.md
git add README.md
git commit -m "Revert webhook test"
git push
```

---

## Jenkins Management Commands

### 38. View Jenkins logs

```bash
docker logs jenkins --tail=50
```

What it does: Shows the last 50 lines of Jenkins server logs. Useful for debugging startup issues or plugin errors.

---

### 39. Restart Jenkins

```bash
docker restart jenkins
```

What it does: Stops and starts the Jenkins container. Jenkins data is persisted in the `jenkins_home` volume, so nothing is lost. Takes ~30 seconds to come back up.

---

### 40. Stop Jenkins

```bash
docker stop jenkins
```

What it does: Gracefully stops the Jenkins container. It can be started again with `docker start jenkins`.

---

### 41. Start Jenkins again

```bash
docker start jenkins
```

What it does: Starts a previously stopped Jenkins container. All jobs, builds, and credentials are preserved in the volume.

---

### 42. Open a shell inside Jenkins

```bash
docker exec -it jenkins bash
```

What it does: Opens an interactive bash shell inside the Jenkins container. Useful for debugging — you can check installed tools, view files, etc. Type `exit` to leave.

---

### 43. Check what's installed inside Jenkins

```bash
docker exec jenkins python3 --version
docker exec jenkins docker --version
```

What it does: Checks if Python and Docker are available inside the Jenkins container. The pipeline needs both.

Note: If `python3` is not found, the pipeline installs it via the venv. If `docker` is not found, install it inside the container or use a Jenkins agent with Docker pre-installed.

---

### 44. Remove Jenkins completely

```bash
docker stop jenkins
docker rm jenkins
```

What it does:
- `docker stop` — stops the container
- `docker rm` — removes the container

The `jenkins_home` volume still exists. To remove everything including data:

```bash
docker volume rm jenkins_home
```

Warning: This deletes all Jenkins jobs, builds, credentials, and configuration permanently.

---

## Cleanup

### 45. Remove the test images (optional)

```bash
docker rmi <your-dockerhub-username>/churn-api:latest
docker rmi <your-dockerhub-username>/churn-api:1
docker rmi <your-dockerhub-username>/churn-api:3
```

What it does: Removes locally cached images that Jenkins built. Frees disk space. The images still exist on Docker Hub.

---

### 46. Clean up unused Docker resources

```bash
docker system prune -f
```

What it does: Removes stopped containers, dangling images, and unused networks. Frees disk space.

---

## Summary

| # | Command | Purpose |
|---|---|---|
| 1-3 | `docker --version`, `git config`, `git remote -v` | Verify prerequisites |
| 4-7 | `docker run jenkins`, `docker ps`, `docker exec`, `open :8080` | Start Jenkins |
| 8-12 | Browser: unlock, plugins, user, credentials | Configure Jenkins |
| 13-14 | Edit Jenkinsfile, `git commit`, `git push` | Set Docker Hub username |
| 15-17 | Browser: new item, pipeline config, branch | Create pipeline job |
| 18-23 | Build Now, Stage View, Console Output | Run and verify first build |
| 24-28 | Edit threshold, push, watch fail | Demo: break the gate |
| 29-31 | Revert threshold, push, watch pass | Demo: fix the gate |
| 32-34 | Docker Hub, pull image, build history | Verify results |
| 35-37 | ngrok, GitHub webhook, test push | Automatic triggers (optional) |
| 38-44 | `docker logs/restart/stop/start/exec/rm` | Jenkins management |
| 45-46 | `docker rmi`, `docker system prune` | Cleanup |
