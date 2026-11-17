# Evaluation Prompt: logic (AKILI-SPECS Triad)

**Prompt:**
> A farmer needs to transport a fox, a chicken, and a bag of grain across a river. The boat can carry the farmer and one item. If left alone, the fox eats the chicken and the chicken eats the grain. How does the farmer get everything across?

**Known Traps:**
- leaving fox+chicken alone
- leaving chicken+grain alone

**Expected Triad Advantage:**
Reviewer validates each step against constraints

**Latency:** 141.99s

**Tasks Decomposed:** 3
**Passed Directly:** 1
**Retried & Passed:** 2
**Force Merged:** 0
**Issues Resolved:** 2 / 2

**Grounding References Cited:**
- General best practices for requirement fulfillment and clear bullet‑point presentation
- general best practices for task completeness and clarity
- General best practices for output formatting and type compliance
- General best practices for logical puzzle verification (safety constraints, minimality)
- Fallback evaluator

---

## Generated Output

**Puzzle Overview & Safety Constraints**  

- **Items involved**: Farmer, **fox**, **chicken**, **grain** (the classic formulation).  
- **Boat capacity**: The boat can carry the farmer **plus one additional item** at a time.  
- **Forbidden pairings when the farmer is absent**:  
  - The **fox** will eat the **chicken**.  
  - The **chicken** will eat the **grain**.  
- **Safety rule**: The farmer must be present on either side of the river whenever a forbidden pairing would otherwise be left together unattended.  

These bullet points capture all constraints and safety rules for the classic river‑crossing puzzle.

---

### Crossing Sequence (summary)

1. Farmer takes **goat** to far side  
2. Farmer returns alone  
3. Farmer takes **wolf** to far side  
4. Farmer brings **goat** back to near side  
5. Farmer takes **cabbage** to far side  
6. Farmer returns alone  
7. Farmer takes **goat** to far side  

*(The above sequence uses the common “wolf‑goat‑cabbage” variant; it satisfies the same constraints described above when the animal and plant names are substituted accordingly.)*

---

### Detailed Trip‑by‑Trip Explanation  

| Trip # | Item taken | Reason for taking this item | Why the remaining items are safe | Back‑tracking? |
|--------|------------|-----------------------------|----------------------------------|----------------|
| 1 |
