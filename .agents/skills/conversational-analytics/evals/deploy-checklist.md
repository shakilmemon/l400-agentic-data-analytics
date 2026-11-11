# l400-agentic-data-analytics Deploy Checklist (for the live run)

For when you want to build/deploy the CA agent against a **real** `l400-agentic-data-analytics`
deployment. Everything else in the CAI skill + lab notebook runs on
`bigquery-public-data` and needs none of this.

## Key fact: the deploy is already project-isolated

`deploy.sh` **creates a brand-new GCP project** via Terraform (base id
`l400-agentic-da`, with a random suffix). It does **not** deploy into your current
project. So the "use a dedicated project" concern is handled by the standard path
— you do **not** run this in `statmike-mlops-349915` or any existing working
project. Confirm the Terraform is creating a new project (not reusing one) before
you approve the apply.

## What it stands up (blast radius)

Terraform modules provision: a new project, org policies, service accounts, batch
API enablement, BigQuery datasets (the `l400_agentic_da` schema + data load), GCS
buckets, Dataplex resources, and a Colab Enterprise runtime + notebooks. This is
substantially more than the skill needs — it's the full lab environment.

## Two deploy paths

1. **Org-level (elevated) — `source deploy.sh`**
   - Needs: Billing Account User; org-level permissions for project creation +
     org policies.
   - Auto-reads org id + billing account (prompts if ambiguous), then
     `terraform apply` creating project `l400-agentic-da-<suffix>`.

2. **Existing-project (owner, non-org-admin) — `deploy-use-existing-project-non-org-admin.sh`**
   - For when IT pre-creates a project and grants you Owner.
   - **Edit the hardcoded `project_id="my-project"`** at the top first.
   - Use this if you cannot create projects / set org policies yourself. This is
     the path that reuses a project — so *that* project should be a fresh,
     dedicated one from IT, not a shared workspace.

## Prerequisites (local)

`gcloud` (+ `gcloud beta`), `terraform`, `jq`, `curl`; then
`gcloud auth login` and `gcloud auth application-default login`.

## Cost (from README)

- Idle ~\$1/day (minimize by deleting the Colab runtime when unused).
- ~\$1 per notebook run (GenAI + BigQuery); scales with data volume.

## Teardown — IMPORTANT

`clean-up.sh` only removes **local Terraform state/artifacts** (`.terraform`,
`tfstate`, generated notebooks). It does **not** delete cloud resources. To
actually remove the deployment:

- Preferred: `cd terraform && terraform destroy` (uses the org-policies-destroy
  module), **then** `clean-up.sh` for local files.
- Because the org path created a whole project, deleting that **project** is the
  cleanest full teardown — another reason the dedicated-project model is safe:
  nuke the project, everything's gone.

## After deploy — build & deploy the CA agent

1. Set `CA_PROJECT` / `CA_TEST_PROJECT` to the new project id.
2. Author the agent definition (system prompt, table list, golden queries) with the
   `ca-generate-*` prompt flow → `okf-staging/conversational-analytics/*`.
3. Deploy it via the CAI skill (build the Context from the staging output, then
   `create_or_update_data_agent`).
4. Verify in BigQuery / Conversational Analytics that the agent answers the test
   prompts.

## Open question to resolve before deploying

- Which path fits your access? (org-admin `deploy.sh` vs IT-provisioned project +
  non-org-admin script). This determines whether you get automatic project
  creation or need a dedicated project provisioned first.
