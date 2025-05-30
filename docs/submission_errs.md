
# Submission Errors
```
KISS-1
{"error":"Failed to submit task result","details":{"error":"Error checking for existing entry.","details":"invalid input syntax for type uuid: \"KISS-1\""}}
```

```
uuid4()
{"error":"Failed to submit task result","details":{"error":"Failed to insert result.","details":"insert or update on table \"completed_runs\" violates foreign key constraint \"completed_runs_run_id_fkey\""}}
```

# Parallel Errors

Running an agent on Omnizon only in parallel:

```
    "err_msg": "Exception uncaught by agent or environment in task webclones.omnizon-9.\nValueError:\nValidation endpoint not yet available",
    "stack_trace": "Traceback (most recent call last):\n  File \"/Users/greg/Documents/GitHub/agiinc/webagent/.venv/lib/python3.11/site-packages/agisdk/REAL/browsergym/experiments/loop.py\", line 278, in run\n    step_info.from_step(env, action, obs_preprocessor=agent.obs_preprocessor)\n  File \"/Users/greg/Documents/GitHub/agiinc/webagent/.venv/lib/python3.11/site-packages/agisdk/REAL/browsergym/experiments/loop.py\", line 401, in from_step\n    self.obs, self.reward, self.terminated, self.truncated, env_info = env.step(action)\n                                                                       ^^^^^^^^^^^^^^^^\n  File \"/Users/greg/Documents/GitHub/agiinc/webagent/.venv/lib/python3.11/site-packages/gymnasium/wrappers/common.py\", line 125, in step\n    observation, reward, terminated, truncated, info = self.env.step(action)\n                                                       ^^^^^^^^^^^^^^^^^^^^^\n  File \"/Users/greg/Documents/GitHub/agiinc/webagent/.venv/lib/python3.11/site-packages/gymnasium/wrappers/common.py\", line 393, in step\n    return super().step(action)\n           ^^^^^^^^^^^^^^^^^^^^\n  File \"/Users/greg/Documents/GitHub/agiinc/webagent/.venv/lib/python3.11/site-packages/gymnasium/core.py\", line 327, in step\n    return self.env.step(action)\n           ^^^^^^^^^^^^^^^^^^^^^\n  File \"/Users/greg/Documents/GitHub/agiinc/webagent/.venv/lib/python3.11/site-packages/agisdk/REAL/browsergym/core/env.py\", line 578, in step\n    reward, done, user_message, task_info = self._task_validate()\n                                            ^^^^^^^^^^^^^^^^^^^^^\n  File \"/Users/greg/Documents/GitHub/agiinc/webagent/.venv/lib/python3.11/site-packages/agisdk/REAL/browsergym/core/env.py\", line 603, in _task_validate\n    reward, done, user_message, info = self.task.validate(self.page, self.chat.messages)\n                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/Users/greg/Documents/GitHub/agiinc/webagent/.venv/lib/python3.11/site-packages/agisdk/REAL/browsergym/webclones/base.py\", line 198, in validate\n    env_state_json = self.get_finish_json(timeout=timeout)\n                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/Users/greg/Documents/GitHub/agiinc/webagent/.venv/lib/python3.11/site-packages/agisdk/REAL/browsergym/webclones/base.py\", line 175, in get_finish_json\n    raise ValueError(error_message)\nValueError: Validation endpoint not yet available\n",
    "completed": true,
```

# Timeout Errors

Due to some timezone issues in some evals, I need to use a US VPN, as such, loading times are quite variable. The defualt timeout seems to be set to 5000ms instead of the default 30. I've noted that `AbstractWebCloneTask.setup()` can timeout and cause a task to fail in this case. Particularly for the `self.background_page.goto(config_url)` line. Setting `AbstractBrowserTask.timeout` to 30000ms fixes this issue.
