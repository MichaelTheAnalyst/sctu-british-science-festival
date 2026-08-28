# British Science Festival 2026 survey

This document is the source of truth for the public Qualtrics survey. Question identifiers in parentheses are the required Qualtrics data-export tags.

## Welcome

Welcome to the British Science Festival 2026!

We would like to collect some anonymous data to show how a growing dataset can help us look for patterns and test ideas.

The first seven questions ask about demographics and preferences. Your answers will help build the charts on the big screen during the day. You can skip any question.

You can then choose whether to take a short six-question quiz about clinical trials. The complete activity should take about 1–2 minutes.

Your results will be added to the grouped data displayed on the big screen. Individual answers will not be shown. Let’s begin!

## Demographics

### Q1. What age band are you? (`AGE_GROUP`)

- 0–15 years old — Seedling scientist
- 16–24 years old — Root researcher
- 25–49 years old — Trunk technician
- 50+ years old — Canopy collaborator
- Prefer not to say — Shy sapling

### Q2. Which hand do you use most often? (`HANDEDNESS`)

- Right — I write with my right hand
- Left — Left is best for me
- Both — I use both hands about equally
- Prefer not to say

### Q3. Which description best matches where you live? (`HOME_AREA`)

- A city
- A town
- A village or rural area
- Prefer not to say

## Preferences

### Q4. How would you usually cut a pizza into slices? (`PIZZA_METHOD`)

- Pizza cutter
- Scissors
- Knife

### Q5. Which creature do you most identify with? (`CREATURE`)

- Cat
- Kangaroo
- Walrus

### Q6. If you weren’t at the science festival today, where would you most like to spend the day? (`DAY_OUT`)

- Shopping in Southampton
- Relaxing on Bournemouth beach
- Walking in the New Forest

### Q7. How do you prefer to communicate? (`COMMUNICATION`)

- Call me!
- I’ll come and chat to you
- Can I answer in a survey, please?

## Optional quiz invitation

That is all the information we will use to build the charts on the big screen. Would you like to take a short quiz about clinical trials?

### Q8. Would you like to carry on? (`CONTINUE_QUIZ`)

- Yes, please — I love learning
- No, thanks — my fingers ache

If the participant answers **No**, end the survey with:

> Thanks for taking part. Your anonymous answers will be added to the grouped data on the big screen. Please ask us about the data, the results you see, or clinical trials in general.

If the participant answers **Yes**, continue to Q9.

## Clinical trial knowledge

Each quiz question should appear on its own page. After an answer is submitted, show the explanation before continuing. The explanation should be shown whether the participant was right or wrong, with a short **Correct** or **Not quite** heading.

### Q9. Can I stop participating in a clinical trial at any time? (`TRIAL_STOP`)

- No — once you have signed up, you must stay in the study
- Maybe — if you can provide a good reason
- Yes — you can stop without giving a reason **(correct)**

Feedback:

> You are in control of your involvement and can stop at any time without giving a reason. The decision is yours, should not affect the standard of care you receive, and you should only continue while you feel happy and able to do so.

### Q10. Is a new treatment always better than the existing treatment? (`NEW_TREATMENT`)

- Yes — a trial will always show that the new treatment is better
- No — a new treatment is not always better **(correct)**
- Not sure

Feedback:

> A new treatment is not always better. That is one of the reasons trials are needed. A “negative” result is still valuable information and can influence how the next trial is designed.

### Q11. What is a randomised controlled trial? (`RANDOMISED_TRIAL`)

- A lottery system that decides who is allowed to take part
- A trial in which a computer randomly assigns participants to treatment groups **(correct)**
- A trial in which each participant chooses their treatment group

Feedback:

> Random assignment creates groups that can be compared fairly. Participants would never receive less than the standard treatment they would normally receive. Some trials also use blinding, which means participants, researchers, or both may not know which treatment was assigned until the appropriate time.

### Q12. What are baseline characteristics? (`BASELINE_CHARACTERISTICS`)

- Information collected at the start of a study so later measurements can be compared with it **(correct)**
- A measure of how funky a guitar sounds
- A person’s heart rhythm recorded on an ECG

Feedback:

> Baseline characteristics describe participants at the start of a study and help researchers identify changes over time and compare groups fairly. The information collected should be relevant to the trial, and researchers aim to collect only what is needed.

### Q13. What is computer system validation? (`SYSTEM_VALIDATION`)

- Telling a database that it is loved
- Testing and documenting that a computer system is accurate, reliable and secure **(correct)**
- An AI system deciding whether a treatment is safe

Feedback:

> Computer system validation uses planned tests, checks and documentation to show that a system works as intended, produces reliable records and protects trial data. It validates the system—not whether a treatment itself is safe or effective.

### Q14. What is a placebo? (`PLACEBO`)

- Something made to look like the treatment being studied but containing no active treatment **(correct)**
- A document describing everything that will happen in a trial
- A popular band from the 1990s

Feedback:

> A placebo is designed to look like the treatment being studied but contains no active treatment. Comparing groups can help researchers separate the treatment’s effects from expectations and other changes. Placebos are only used when it is ethical and safe; participants would not be denied necessary standard treatment.

## Final message

Thanks for completing the clinical-trials quiz. We hope you learned something new!

Do not forget to see how the growing dataset on the big screen develops during the day. Please ask us about the data, the results you see, or clinical trials in general.

## Required survey flow

1. Welcome text.
2. Q1–Q7.
3. Q8 on a separate page.
4. If Q8 is **No**, show the short thank-you message and end the survey.
5. If Q8 is **Yes**, show Q9–Q14, one question per page, with feedback after every answer.
6. Show the final message.

## Dashboard relationships

- Q4 pizza method by Q2 handedness.
- Q5 creature by Q2 handedness.
- Q6 preferred day out by Q3 home area.
- Q7 communication preference by Q1 age band.
- All public charts must show grouped totals only.
- For very small groups, show counts rather than percentages and avoid claiming a meaningful relationship.
