# Instantiation Checklist

The tickable form of `INSTANTIATION-GUIDE.md`. Work an install from this
list, copied into a deployment ledger (`templates/ledger.template.md`); each
item is checked on its own, which keeps a long install from drifting.

## Preconditions

- [ ] The user asked for the install (law L8)
- [ ] Capabilities resolved (`BOOTSTRAP.md` §1)
- [ ] Path chosen: greenfield (guide §3), retrofit (§4), or skeleton only

## Inputs (guide §1 steps 1–3)

- [ ] Rule documents and their prefixes, one per seam (greenfield: plus
      the dev-environment document)
- [ ] Project name (`dev-instructions.yaml`, or asked)
- [ ] Active module chosen with the user; its checkout found
- [ ] The catalyst-users provider confirmed, and the installer logged in to it

## Install (guide §1 steps 4–5)

- [ ] `catalyst init` exited `0`
- [ ] The module's `INVARIANTS.module.md` read
- [ ] `catalyst agent install <agent>` run once on this machine; nothing
      written into the project but `catalyst.toml`
- [ ] `catalyst hook install` and, with CI, a `catalyst trace` step offered;
      run only on the user's yes

## Content (guide §1 steps 6–8)

- [ ] Placeholders the module requires filled by the command it names
- [ ] Root `README.md` extended with the project's structure
- [ ] Greenfield: each decision area a domain and its rules, implemented
      and running clean; `{{TEST_LOCATIONS}}` resolved
- [ ] Retrofit: rules gathered from the code, conflicts asked, not decided
- [ ] Starter artifacts the module's meta-rules call for, tied to concrete
      screens, flows or components
- [ ] Every change journaled

## Done

- [ ] `dev-instructions.yaml` deleted; the deployment noted in memory if a
      store exists (guide §6)
- [ ] `catalyst check`: no errors; warnings reported
- [ ] Every item above ticked in the ledger, none skipped silently
- [ ] Deployed tree presented; nothing committed or pushed (law L3)
- [ ] Retrofit with no work items yet: `/run-analysis --bootstrap` offered
