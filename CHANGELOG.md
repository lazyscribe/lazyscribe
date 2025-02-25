## v1.0.1 (2025-02-25)

### Fix

- remove duplicate path to artifact in loading (#122)
- address handling of exact matches for the 'asof' match (#121)

## v1.0.0 (2025-02-24)

### Feat

- creating the directory for the project JSON if it doesn't exist
- **repository**: `asof` version matching to allow users to get the latest version of an artifact as of a given datetime (#110)
- Replace `RuntimeError` with custom errors (#108)
- using a new `dirty` flag to describe whether an artifact or experiment needs to be persisted (#98)

### Fix

- exclude `.dirty` from validations (#115)
- make objects dirty by default
- handle string project filepaths (#107)

### Refactor

- get rid of re-raise (#119)
- refactor exceptions hierarchy (#112)

## v0.7.1 (2025-02-15)

### Fix

- adding a check to ensure existing artifacts are not overwritten with null data and removing the w+ mode (#96)

## v0.7.0 (2025-02-13)

### Feat

- Add repository for artifact storage (#81)

## v0.6.0 (2024-10-30)

### Feat

- added `output_only` option to the Artifact base class (#55)
- added ability to use entry points to specify dynamic artifact handlers (#56)
- implement parameters for `Test` (#60)

### Fix

- enable parameterized project paths in Prefect (#58)

## v0.5.0 (2024-05-29)

### Breaking Changes

- changed the field names for `Project.to_tabular` output to explicitly label Experiment vs. Test-level fields (#41)

### Feat

- ability to tag and filter experiments (#43)

## v0.4.0 (2023-06-01)

### Feat

- improved performance on project load through caching dependencies (#21)
- associating artifacts directly with experiments through generic handlers

## v0.3.2 (2023-01-31)

### Feat

- added ability to interact with remote filesystems through ``fsspec``

## v0.3.1 (2022-11-24)

### Fix

- added explicit testing and support for Python 3.10

## v0.3.0 (2022-04-02)

### Feat

- Prefect integration (#8)

## v0.2.0 (2022-03-04)

### Feat

- ability to log non-global metrics (#4)
- conversion of experiments and tests to lists for conversion to pandas (#5)
