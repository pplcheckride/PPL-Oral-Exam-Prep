# QUICK START GUIDE - What to Do Right Now

**Last Updated:** February 6, 2026

---

## IMMEDIATE ACTION (Do This First - 30 Minutes)

### Step 1: Migrate to Netlify (URGENT - TOS Violation)

**Why:** GitHub Pages prohibits commercial use. Your site could be taken down.

**How:**
1. Go to netlify.com
2. Sign up with GitHub account
3. Click "Add new site" → "Import from Git"
4. Select repository: `pplcheckride/PPL-Oral-Exam-Prep`
5. Build settings: Leave blank (just HTML, no build needed)
6. Click "Deploy"
7. Wait 2 minutes for deployment

**Update DNS:**
1. Go to Netlify site settings → Domain management
2. Add custom domain: `pplcheckride.com`
3. Netlify gives you DNS instructions
4. Go to Namecheap → Domain List → Manage → Advanced DNS
5. Delete old A records (GitHub IP addresses)
6. Add Netlify's DNS records (they provide these)
7. Wait 10-30 minutes for DNS propagation
8. Test: Visit pplcheckride.com (should load from Netlify)

**Disable GitHub Pages:**
1. GitHub repo → Settings → Pages
2. Source: None
3. Save

**Done!** You're now TOS compliant.

---

## THIS WEEK (Priority Tasks)

### Task 1: Write Test Scenarios (Days 1-2)

**Goal:** Validate you can write quality scenarios before committing to 100

**Steps:**
1. Open AI_Question_Generator_Prompt.txt
2. Copy entire contents
3. Paste into ChatGPT/Claude
4. Run: "Generate 10 scenario-based questions focusing on Pro-rata share and pilot privileges"
5. Review output for quality
6. Show 3-5 scenarios to your CFI
7. Ask: "Are these realistic? Would a DPE ask like this? Any regulatory errors?"

**Decision Point:**
- If CFI says "yes, these are good" → Continue to 100 scenarios
- If CFI says "these need work" → Adjust prompt/approach

### Task 2: Build Question Library (Days 3-7)

**Target:** 50 scenarios minimum for launch

**Batch Topics (10 each):**
1. Pro-rata share & pilot privileges
2. Night currency & fuel reserves
3. Class B/C/D airspace entry
4. BasicMed vs. 3rd class medical
5. Inoperative equipment (91.213)

**Daily Pace:** 10 scenarios/day (1.5 hours)

**Quality Check:**
- Every 20 scenarios, show batch to CFI
- Fix any regulatory errors immediately
- Don't continue if quality is declining

---

## NEXT WEEK (Launch Preparation)

### Task 3: Build License Key System (Days 8-9)

**Gumroad Setup:**
1. Create product: "PPL Checkride - DPE Scenario Simulator"
2. Price: $57
3. Enable License Keys (Product → Settings → License Keys)
4. Customize email template with license key

**App Integration:**
1. Add unlock modal UI to index.html
2. Integrate Gumroad License Verify API
3. localStorage unlock logic
4. Test flow: Buy → Get key → Enter key → Unlock

**Testing Checklist:**
- [ ] Valid key unlocks app
- [ ] Invalid key shows error
- [ ] Refunded purchase gets denied
- [ ] Unlock persists after page reload
- [ ] Free version shows upgrade prompts

### Task 4: Finish Content (Days 10-12)

**Write final 50 scenarios to reach 100 total**

**Topics:**
- Weather decisions (METAR/TAF)
- Aircraft systems & performance
- Emergency procedures
- NTSB reporting
- Flight planning

### Task 5: Polish & Launch (Days 13-14)

**Pre-Launch Checklist:**
- [ ] 100 scenarios written and validated
- [ ] License key system tested
- [ ] Free version shows 10 questions
- [ ] Paid version shows 100 questions
- [ ] Mock checkride works (30 questions, 30 min, 80% pass)
- [ ] Analytics installed (Plausible or GA4)
- [ ] Gumroad product live
- [ ] Launch post drafted for r/flying

**Launch Day:**
1. Post on r/flying (authentic, helpful, not salesy)
2. Share in Facebook aviation groups
3. Email link to flying friends
4. Monitor for first sales
5. Respond to questions/feedback

---

## FILES YOU NEED

**Essential Files (All Provided):**
1. **index.html** - Fixed production app (deploy this to Netlify)
2. **PROJECT_SUMMARY_COMPLETE.md** - Full context document (read this first)
3. **AI_Question_Generator_Prompt.txt** - For generating scenarios
4. **BUG_FIXES_SUMMARY.md** - What bugs were fixed

**Optional:**
5. **Private_Pilot_Oral_Exam_-_10_Essential_Questions__FREE_.html** - Lead magnet (convert to PDF later)

---

## DECISION POINTS

### Decision 1: How Many Scenarios at Launch?

**Option A: 50 scenarios (Ship in 1 week)**
- Faster to market
- Less content risk
- Can validate demand quickly
- Add 10/week post-launch

**Option B: 100 scenarios (Ship in 2 weeks)**
- More complete product
- Stronger value prop
- Fewer updates needed initially
- Longer validation wait

**Recommendation:** Start with 50, add 50 more in first month

### Decision 2: Pricing

**Conservative: $47**
- Easier to justify at launch
- Lower barrier to first customers
- Can increase later as library grows

**Target: $57**
- Sweet spot for quality positioning
- Not too high to scare away, not too low to seem cheap
- Room to grow to $77-97

**Premium: $67**
- Strong quality signal
- Justified by scenario uniqueness
- Higher margin per sale

**Recommendation:** $57 at launch

### Decision 3: Free Lead Magnet

**Option A: 10-question PDF**
- Traditional lead magnet approach
- Requires email to download
- Build email list

**Option B: Full app with 10 questions**
- No email gate (lower friction)
- Users experience actual product
- Better conversion (try before buy)

**Recommendation:** Option B (full app, 10 questions, no email required)

---

## COMMON MISTAKES TO AVOID

1. **Don't launch on GitHub Pages**
   - Violates TOS, site could be taken down
   - Migrate to Netlify FIRST

2. **Don't skip CFI validation**
   - You're a student pilot, not a DPE
   - Regulatory errors kill credibility

3. **Don't use two separate URLs**
   - Looks unprofessional
   - Creates piracy risk
   - Use single URL + license key

4. **Don't over-complicate license keys**
   - Gumroad API is simple
   - Don't build custom backend
   - localStorage is fine for v1

5. **Don't launch without testing unlock flow**
   - Broken unlock = instant refunds
   - Test with real Gumroad purchase

6. **Don't write 500 scenarios before launch**
   - Massive time investment without validation
   - Launch with 50-100, expand post-launch

---

## WEEK 1 DAILY PLAN

**Monday:**
- [ ] Migrate to Netlify (30 min)
- [ ] Generate 10 test scenarios (1 hour)
- [ ] Send scenarios to CFI for review

**Tuesday:**
- [ ] Get CFI feedback
- [ ] Adjust approach if needed
- [ ] Generate 20 more scenarios (2 hours)

**Wednesday:**
- [ ] Generate 20 scenarios (2 hours)
- [ ] Total: 50 scenarios complete

**Thursday:**
- [ ] Set up Gumroad product (1 hour)
- [ ] Enable license keys
- [ ] Test purchase flow

**Friday:**
- [ ] Build unlock modal UI (3 hours)
- [ ] Integrate Gumroad API (2 hours)

**Weekend:**
- [ ] Test license key system
- [ ] Generate final 50 scenarios (4 hours)
- [ ] Write launch post

---

## ANALYTICS SETUP (Optional - 15 min)

**Recommended: Plausible Analytics ($9/mo)**

**Setup:**
1. Sign up at plausible.io
2. Add site: pplcheckride.com
3. Copy tracking script
4. Add to <head> of index.html:
   ```html
   <script defer data-domain="pplcheckride.com" src="https://plausible.io/js/script.js"></script>
   ```
5. Deploy updated index.html

**Alternative: Google Analytics 4 (Free)**
1. Create GA4 property
2. Get measurement ID (G-XXXXXXXXXX)
3. Add tracking code to index.html
4. Deploy

**What to Track:**
- Daily visitors to free version
- Clicks on "Unlock Full Version"
- Traffic sources (Reddit, direct, Google)
- Mock checkride completions

---

## SUPPORT & RESOURCES

**If Something Breaks:**
1. Check browser console for errors (F12 → Console)
2. Verify Netlify deployment succeeded
3. Test DNS propagation: whatsmydns.net
4. Check Gumroad API status

**Getting Help:**
- Netlify docs: docs.netlify.com
- Gumroad support: help.gumroad.com
- r/webdev for technical issues
- Your CFI for aviation content

**Backup Plan:**
If license key system is too complex, fall back to:
- Two URLs (free and premium)
- Premium URL has random string
- Still works, just less elegant

---

## SUCCESS METRICS (90 Days)

**Minimum Viable Success:**
- 15 sales @ $57 = $855
- 3+ positive reviews on Reddit/forums
- Zero regulatory accuracy complaints

**Target Success:**
- 50 sales @ $57 = $2,850
- 10+ testimonials from checkride passes
- Word-of-mouth growth starting

**Exceptional Success:**
- 100+ sales @ $57 = $5,700
- Featured in aviation podcasts/YouTube
- Organic backlinks from flight schools

---

END OF QUICK START GUIDE
