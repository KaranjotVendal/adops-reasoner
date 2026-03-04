# Stacked PR Execution Playbook (Latest)

```text
main
 └─ pr/01-scaffold-contracts-data
     └─ pr/02-analyzer-core
         └─ pr/03-validator-orchestration
             └─ pr/04-evals-demo
                 └─ pr/05-terraform-minimal
                     └─ pr/06-cicd-ghcr-cloudrun
```

## PR #1
Scaffold project + domain contracts + synthetic dataset
- tests: model validation + generator tests

## PR #2
Analyzer agent + provider abstraction (MiniMax primary)
- tests: analyzer parsing + API contract

## PR #3
Validator agent + orchestration policy (`requires_human_review`)
- tests: validator conflicts + low-confidence gating

## PR #4
Offline eval harness + demo payload scripts
- tests: metric correctness

## PR #5
Minimal Terraform (Cloud Run + Secret Manager + IAM SA)
- tests: `terraform fmt -check`, `terraform validate`

## PR #6
GitHub Actions CI/CD (lint/test/build/push GHCR/deploy Cloud Run)
- tests: workflow green + deployed health smoke test

## Definition of done
- one purpose per PR
- tests included
- CI green
- docs updated
- no secrets committed
