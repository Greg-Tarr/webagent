# KISS-1 Development: Achieving 57% Success on REALEvals Benchmark

## Results Overview

KISS-1 scores 57.14% (64/112 tasks) on the REALEvals benchmark. This would have ranked competitively on the open leaderboard, though I ran into submission issues during the final upload. Before you *explode* from excitement, I'd like to caution that the primary reason for such a high score isn't that KISS-1 is a sophisticated framework, but likely just that it's using a more modern model than the benchmarks (Sonnet 4). Further, the agent expends a ludicrous amount of time thinking - it really doesn't stop until it's solved the issue or runs out of time. The longest running task that ended up being successful went on for a staggering 30 minutes! Unfortunately, this led the overall cost to be astronomical - a problem I attempted to solve with a few approaches, but still ended up spending ~$600.

![KISS-1 Demo](assets/demo.gif)

## Development Journey

I started with the basic approach from the hackable.py example adapted for Anthropic tool use - essentially feeding page state (AXTree) to Sonnet 4 and executing whatever action it suggested. This worked remarkably well, and managed to solve a few Omnizon tasks before failing. It's worth mentioning now that budgetary constraints prevented repeatedly testing on the entire set, in fact there was only room in the budget to submit exactly once, meaning I wouldn't be able to test on all of the sites.

The first improvement was using Claude thinking mode: A simple way of exchanging lots of money for an increasingly diminishing return in intelligence. With this enabled, the barriers to improvement primarily become tools & context. I'm generally of the opinion that one should solve problems at their source rather than band-aid them. Most benchmark improvements come from tweaking approaches or adding optimizations, but the real wins come from fixing the actual bottlenecks. Memory, self-critique, and planning are all behaviors that SOTA models already have. If you're struggling with large contexts, the solution is bigger context windows or a completely different approach - not a bunch of string manipulations on top of an already complex system.

But my budget didn't exactly include new architectures and nuclear training runs, so let's see what string manipulations we can get away with!

### Page State & Diffs
First was handling memory. The naive system appended the full AXTree to the conversational history each iteration. Even actions which didn't change the page state whatsoever (e.g. scrolling or screenshots) increased the context length dramatically. This is obviously stupid. Fortunately the problem of tracking incremental changes in a large multiline string was solved a long time ago. Python's `difflib` gives us the ability to return something akin to git's `diff` function. This reduces the overall context length by a lot while still allowing the model to see which elements have appeared or disappeared as a result of its actions.

```
I'll help you search for "PlayStation DualSense" and complete the purchase with the specified payment method. Let me start by closing the alert and then searching for the product.
 
Tool Use 3: click({'bid': '141'})

<state full_reset=False>Page state changes:
--- previous_state+++ current_state@@ -1,8 +1,4 @@ RootWebArea 'Omnizon - Online Shopping for Electronics, Apparel, and More', focused, url='https://evals-omnizon.vercel.app/'
-	[135] alert '', live='assertive', atomic, relevant='additions text'
-		StaticText 'This website is a non-commercial clone created solely for educational and testing purposes and is not affiliated with, endorsed by, or associated with any companies it may resemble.'
-		StaticText 'All trademarks, logos, and content are the property of their respective owners and are used here for academic purposes only, with no intent to infringe on intellectual property rights.'
-		[141] button 'close'
[143] navigation 'Main Navigation'
[144] link 'Home', url='https://evals-omnizon.vercel.app/'
[146] image 'Omnizon Logo', url='https://evals-omnizon.vercel.app/_next/image?url=%2Fimages%2Flogo%2Flogo.png&w=1920&q=75&dpl=dpl_3rm5KvWLrrcqBdCsCtpmpa8khjso'
</state>
```

Here we can see an example of using difflib. Instead of the agent seeing the entire page after closing the banner, we just see that the banner has been removed.

## Long-Term Memory

With some minor prompt improvements, the difflib approach took us pretty far. The issue became extremely long running tasks such as "get the lowest cost item from all of the restaurants" which required the agent to do quite a lot of searching. Sure, I could have built some elaborate memory management system or multi-agent orchestration, but I was trying to keep things simple. I ended up preserving recent tool calls and outputs while pruning old state changes (keeping everything after the last full page reset). This approach let the agent keep going for over 120 iterations before context lengths got unwieldy.

### Error Recovery

Real websites are messy. The benchmark websites are even messier. There are a plethora of bugs and incorrect UI elements that make navigating some of them hard to impossible the first time. I realized at this point that I had been mistakenly filtering out the navigation tools. Upon enabling them and instructing the model to make liberal use of the 'go_back' function, I found a great behavior. Over the course of sometimes up to thirty minutes, the agent would fail, try again, fail, and then `go_back` and change its approach. It did this until it had solved the task or ran out of turns.

In many cases, the agent would get stuck due to inaccessible elements - the compose button being StaticText without a clickable bid in GoMail for example. To fix this, I added screenshot functionality, but made sure the model used it as a last resort. This decision was made not only to conserve tokens, but also because the agent's accuracy in coordinate navigation is substantially less reliable than its ability to simply select a BID.

This allowed the agent to succeed in sending the email, however it was unfortunately still a failure case. I suspect this is another bug in the eval.

```
Criterion 2 correct email content: [
 actual value: <p browsergym_visibility_ratio="1" bid="1193" browsergym_set_of_marks="0">Please find the meeting notes attached.</p>
 expected value: <p>Please find the meeting notes attached.</p> , is_correct: False]
```

The eval inserts custom attributes and doesn't strip them when evaluating. I haven't debugged AGISDK as I haven't the time, but I stopped looking for bugs in the evals after the first three. You can see the other two in `docs/bad_evals`.

### Task Specifics

There was a lot of fine-tuning the prompt for various circumstances. One of the most annoying issues was on OpenDining. It might be a US/Europe issue, but some pages just absolutely don't load, even after a refresh. I had to write a custom action that really aggressively refreshes (and clears caches etc.) to make it work. Getting the model to figure out that seeing skeletons for too long meant that it should probably refresh was easy, but figuring out that hard-refreshes were needed was a real time sink.

Many websites, like Fly Unified for instance, have incorrect UI elements that make the correct answers incredibly unclear and arguably impossible. Further, some dropdowns are inconsistent in whether or not their sub-sub-options have BID values or are accessible.

I realized that finding failure modes in the agent that were not attributable to the eval would be too time consuming and decided to submit.

## Final Results

I was surprised at the results to say the least. I spent several hours trying to figure out why the submission failed, but to no avail.

```
Run Statistics:
 Run UUID: KISS-1
 Total tasks: 112
 From cache: 0
 Newly executed: 112
 Tasks with errors: 0 of 112 (0.0%)

===== BENCHMARK RESULTS =====
Tasks completed successfully: 64/112
Success rate: 57.14%

Timing Statistics (All Tasks):
 Average time: 321.93 seconds
 Median time: 192.41 seconds
 Min time: 31.74 seconds
 Max time: 1830.58 seconds
 Std deviation: 364.66 seconds

Timing Statistics (Successful Tasks Only):
 Average time: 210.08 seconds
 Median time: 145.85 seconds
 Min time: 31.74 seconds
 Max time: 1830.58 seconds
 Std deviation: 241.52 seconds

Results by task type:
 dashdish: 8/11 (72.73%) - Avg time: 121.56s
 fly-unified: 3/14 (21.43%) - Avg time: 666.20s
 gocalendar: 3/10 (30.00%) - Avg time: 700.62s
 gomail: 5/8 (62.50%) - Avg time: 194.89s
 networkin: 8/10 (80.00%) - Avg time: 115.73s
 omnizon: 10/10 (100.00%) - Avg time: 134.93s
 opendining: 9/10 (90.00%) - Avg time: 439.47s
 staynb: 4/9 (44.44%) - Avg time: 349.03s
 topwork: 2/9 (22.22%) - Avg time: 199.24s
 udriver: 8/11 (72.73%) - Avg time: 170.03s
 zilloft: 4/10 (40.00%) - Avg time: 312.08s
```

### Conclusion

I have a feeling the task was to build a Langflow-esque framework with comprehensive retries and multi-agent memory management, but if this project has taught me anything it's that effective engineering is about rigorous, incremental testing. Perhaps with a more comprehensive evaluation set the need for rigorous guardrails would become apparent, but honestly, getting 228% of the target performance with a "keep it simple" approach feels pretty vindicated.

The $600 budget constraint was actually a blessing in disguise - it forced me to focus on what actually moved the needle rather than building elaborate frameworks that might look impressive but don't solve tasks. Sometimes the boring solution that works is better than the sophisticated one that doesn't.

As for next steps, I believe focusing on bringing the cost down would be the priority. I can't speak to meaningful improvements because it was too rare to see a 'good failure' where the eval was definitely not at fault. The agent's behavior when it actually failed due to its own limitations (rather than website bugs) was difficult to analyze.

If I were to rebuild this with unlimited resources, I'd probably explore using a linear-time complexity model like RWKV, with some fancy state-space tricks to manage page contexts cheaply. Setting this up in a semi-synthetic RLHF environment could potentially maintain the performance while making it economically viable for real-world deployment. But that's a very different project than what was asked for here.

For now, KISS-1 proves that you don't always need to overthink the problem - sometimes Claude just wants to think really hard about clicking buttons, and if you let it, it'll figure things out.
