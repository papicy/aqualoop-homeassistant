# Repository contribution instructions

## Before committing or opening a pull request

Do not commit or open a pull request until the local quality checks pass.

1. Install the test dependency when needed:

   ```text
   python -m pip install --upgrade pip pytest-homeassistant-custom-component
   ```

2. Run the complete test suite:

   ```text
   pytest -q
   ```

3. Check the patch for whitespace errors:

   ```text
   git diff --check
   ```

4. Review the staged diff and confirm that the changed files, tests, and PR
   description match the requested behavior.

If Python or the test dependencies are unavailable, report validation as
blocked and do not describe the change as tested or PR-ready.

## Home Assistant test conventions

- Access Home Assistant states with `hass.states.get(entity_id)`. The state
  machine is not subscriptable.
- Assert that a state exists before reading its attributes.
- Verify entity IDs from the actual registered state or entity registry. An
  entity ID can use a translated name such as `active_setpoint` rather than
  the implementation class or translation key name.
- When adding or changing entity metadata, add a focused test and run the
  complete suite before committing.

## Pull requests

Keep PRs focused and describe the user-facing reason, implementation approach,
validation performed, and any remaining limitations. CI runs pytest, Hassfest,
and the HACS Marketplace validation, so local changes should be checked against
all three where practical.
