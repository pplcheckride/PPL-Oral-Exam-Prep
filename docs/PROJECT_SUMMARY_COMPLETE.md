# PPL Oral Exam Prep - Complete Project Summary

**Last Updated:** February 6, 2026  
**Project Owner:** Param (Student Pilot, Data Analytics background)

---

## PROJECT OVERVIEW

**Product Name:** PPL Checkride - DPE Scenario Simulator  
**Domain:** pplcheckride.com  
**Current Status:** Live on GitHub Pages (needs migration - TOS violation)

**What It Is:**
Interactive web app for Private Pilot License oral exam preparation using realistic scenario-based questions that test correlation-level knowledge (not rote memorization).

**Business Model:** Freemium
- Free version: 10 scenario questions, all app features
- Paid version: 100 scenarios at launch (expanding to 500 over 6 months)
- Price: $47-67 one-time payment
- Delivery: Gumroad with license key unlock

---

## MAJOR PIVOT (Critical Change)

**OLD APPROACH (Scrapped):**
- Simple Q&A format: "What documents must you have?" → "PPM - Pilot certificate, Photo ID, Medical"
- Commodity product (competes with free YouTube/Sporty's)
- Low perceived value ($27-37 max)

**NEW APPROACH (Current):**
- Scenario-based DPE simulator questions
- Format: Setup → Complication → Question → Trap Answer → Correct Answer → Explanation → Reference
- Tests APPLICATION of regulations, not just recall
- Unique positioning: "The only oral prep that simulates hard-ass DPE scenarios"
- Premium pricing justified ($47-67)

**Why This Matters:**
First 10 reviews in aviation communities ARE your reputation. A "mediocre but helpful" product gets ignored. A "holy shit this exposed gaps in my knowledge" product gets evangelized.

---

## THREE CRITICAL TASKS

### Task 1: Convert Questions to Scenario Format

**Current State:**
- Have 100 basic Q&A questions (simple format)
- Need to convert to scenario format OR write new scenarios from scratch

**Scenario Format (Required):**
```
Setup: [2-4 sentences setting the scene - aircraft, weather, location, pressure]
Complication: [The "oh shit" moment that forces a decision]
Question: [Direct DPE question]
Trap Answer: [Plausible but WRONG answer based on common misconceptions]
Correct Answer: [Legally/technically correct decision with regulation cited]
Explanation: [Why trap is wrong, why correct is right, educational detail]
Reference: [Specific 14 CFR citation]
Cram Mode: [One-sentence memory aid]
```

**Timeline:** 
- 100 scenarios at 10-15 min each = 16-25 hours
- Realistic pace: 5-10 scenarios/day = 10-20 days
- Launch target: 50 scenarios minimum (add 50 more post-launch)

**Validation Needed:**
- CFI review for regulatory accuracy
- Student pilot testing for difficulty calibration
- Trap answers must actually trap people

### Task 2: Hosting Migration (GitHub Pages → Netlify)

**Current Problem:**
- GitHub Pages Terms of Service PROHIBIT commercial use
- Current setup violates TOS (hosting paid product on Pages)
- Risk: Site could be taken down mid-launch

**Solution: Migrate to Netlify**
- Explicitly allows commercial use
- Free tier: 100GB bandwidth (plenty for this use case)
- Same workflow as GitHub Pages (connect repo, auto-deploy)
- Custom domain support included
- Time to migrate: 30-60 minutes

**Migration Steps:**
1. Sign up for Netlify, connect GitHub repo
2. Configure build settings (none needed - it's just HTML)
3. Update Namecheap DNS to point to Netlify
4. Test deployment
5. Disable GitHub Pages

### Task 3: License Key Unlock System

**Requirement:** Single professional URL, not two separate sites

**User Flow:**
1. User visits pplcheckride.com → Sees free version (10 questions)
2. Clicks "Unlock Full Version" → Modal appears
3. Enters license key from Gumroad purchase
4. App validates key via Gumroad API
5. If valid: Stores unlock in localStorage, reloads page
6. Now sees full version (100+ questions)

**Technical Implementation:**
- Check localStorage on page load: `isUnlocked = localStorage.getItem('ppl-unlocked')`
- If unlocked: Load all questions
- If locked: Load only first 10 questions
- Validate key with Gumroad License Verify API
- Re-validate periodically (every 24 hours) to catch refunds

**Gumroad Setup:**
- Enable License Keys in product settings
- Each purchase auto-generates unique key
- Email template includes: "Your license key: XXXX-XXXX-XXXX"

**Time Estimate:** 8-12 hours (2-3 days)

---

## CURRENT APP STATUS

**Live URL:** pplcheckride.com (hosted on GitHub Pages)

**Features Working:**
- Study Mode: Questions in order (Q1→Q100)
- Random Mode: Shuffled questions
- Review Wrong Answers: Focus on "Need Practice" questions
- Mock Checkride Simulator: 30 questions, 30 minutes, 80% pass threshold
- Performance Insights: Analytics showing readiness
- Progress Tracking: localStorage (Mastered/Review/Practice)

**Critical Bugs FIXED:**
- ✅ Timer was 30 SECONDS (now 30 minutes)
- ✅ Pass threshold was 33% (now 80%)
- ✅ Marginal threshold was 20% (now 70%)

**Files:**
- index.html: The complete app (fixed version provided)
- Single-file architecture (no dependencies except Google Fonts)
- All questions, logic, and styling in one HTML file

---

## TECHNICAL ARCHITECTURE

**Tech Stack:**
- Pure HTML/CSS/JavaScript (no frameworks)
- Single-file app (easy to update, no build process)
- localStorage for progress tracking
- Google Fonts for typography
- No backend (except license validation calls to Gumroad API)

**Hosting:**
- Current: GitHub Pages (MUST MIGRATE)
- Target: Netlify (TOS compliant, free tier)

**Payment/Delivery:**
- Gumroad for payment processing
- License key generation (automatic)
- Email delivery with key

**Domain:**
- Registered: pplcheckride.com (Namecheap)
- DNS configured for GitHub Pages (needs update for Netlify)

---

## QUESTION GENERATION STRATEGY

**Target:** 100 scenarios for launch, 500 total over 6 months

**Content Distribution (100 scenarios):**
- Certificates & Documents: 10
- Airworthiness: 10
- Weather: 15
- Airspace: 15
- Regulations: 15
- Flight Planning: 10
- Aircraft Systems: 10
- Emergency Procedures: 10
- Human Factors: 5

**Quality Requirements:**
- Each scenario tests CORRELATION level (application, not recall)
- Realistic complications (passenger pressure, equipment failure, time pressure)
- Plausible trap answers based on common misconceptions
- Accurate FAA regulation citations (14 CFR, NTSB 830, AIM)
- CFI validation required

**Generation Method:**
- AI-assisted (using provided prompt template)
- Human review for accuracy
- CFI spot-check for realism
- Student pilot testing for difficulty

---

## LAUNCH STRATEGY

**Timeline:** 2-week sprint to launch

**Week 1:**
- Days 1-2: Write 10 test scenarios, get CFI validation
- Day 3: Migrate to Netlify (1 hour)
- Days 4-7: Write 40 more scenarios (50 total)

**Week 2:**
- Days 8-9: Build license key system
- Days 10-12: Write final 50 scenarios (100 total)
- Days 13-14: Polish, test, launch

**Post-Launch:**
- Add 10 scenarios/week via updates
- Email customers about new content
- Build to 200, then 300, then 500 over 6 months
- Potential price increase as library grows

**Marketing:**
- r/flying organic post (authentic, not salesy)
- Facebook aviation groups
- Free 10-question PDF lead magnet
- Word-of-mouth from early users

---

## BUSINESS GOALS

**90-Day Validation:** 15 sales organic-only (no ads)

**Success Metrics:**
- Product quality drives word-of-mouth
- First reviews are 4-5 stars (reputation crucial)
- Students report "this exposed gaps I didn't know I had"
- Organic growth via aviation communities

**Pricing Strategy:**
- Launch: $47-67 (100 scenarios)
- Month 3: $77-87 (250 scenarios) - early buyers grandfathered
- Month 6: $97-127 (500 scenarios) - early buyers still pay $47

**Revenue Projection:**
- Conservative: 15 sales @ $47 = $705 (validates market)
- Target: 50 sales @ $57 = $2,850 (90 days)
- Optimistic: 100 sales @ $67 = $6,700 (6 months)

---

## KEY LEARNINGS & PRINCIPLES

**From User's Background:**
- Validation-first approach (ship early, iterate based on feedback)
- Authentic marketing > gimmicky tactics
- First impressions crucial in aviation communities
- Quality over speed for launch reputation
- Digital-only, asynchronous products (no live instruction)

**Product Philosophy:**
- Sophisticated scenarios justify premium pricing
- Basic Q&A is a commodity (YouTube, Sporty's)
- Unique = "DPE Scenario Simulator" positioning
- Students will pay to avoid checkride failure ($500+ re-test cost)

**Technical Principles:**
- Single-file architecture (easy maintenance)
- No complex backend (reduces moving parts)
- Client-side only where possible
- Progressive enhancement (start simple, add features)

---

## RISKS & MITIGATIONS

**Risk 1: Can't write 100 quality scenarios in 2 weeks**
- Mitigation: Launch with 50, add 10/week post-launch
- Minimum viable: 30 scenarios (just Mock Checkride mode)

**Risk 2: GitHub Pages shuts down site mid-launch**
- Mitigation: Migrate to Netlify IMMEDIATELY (30 min task)
- Critical: Do this before launch, not after

**Risk 3: License key system too complex/buggy**
- Mitigation: Use proven Gumroad API, test extensively
- Fallback: Separate URLs if license keys fail (less professional)

**Risk 4: CFI says scenarios aren't realistic**
- Mitigation: Get early validation (write 10, get feedback)
- Adjust approach before writing all 100

**Risk 5: Aviation community rejects as "too hard"**
- Mitigation: Market as "advanced/serious" not "beginner"
- Target: Students close to checkride, not day-1 students

---

## FILES PROVIDED

1. **index.html** - Fixed production app (bugs corrected, ready to deploy)
2. **BUG_FIXES_SUMMARY.md** - Details on critical bug fixes
3. **AI_Question_Generator_Prompt.txt** - Complete prompt for generating scenarios
4. **Private_Pilot_Oral_Exam_-_10_Essential_Questions__FREE_.html** - Lead magnet PDF (needs conversion)

---

## NEXT IMMEDIATE STEPS

**Priority 1: Hosting Migration (Today - 30 min)**
1. Sign up for Netlify
2. Connect GitHub repo
3. Update DNS to Netlify
4. Verify site loads
5. Disable GitHub Pages

**Priority 2: Question Generation (Week 1)**
1. Write 10 test scenarios using provided format
2. Show to CFI for validation
3. Adjust based on feedback
4. Write remaining 40-90 scenarios

**Priority 3: License Key System (Week 2)**
1. Set up Gumroad product with license keys
2. Build unlock modal UI
3. Integrate Gumroad License API
4. Test unlock flow end-to-end
5. Handle edge cases (invalid key, refund, etc.)

**Priority 4: Launch Preparation**
1. Write r/flying launch post
2. Set up analytics (Plausible recommended, $9/mo)
3. Create free PDF lead magnet (convert HTML to PDF)
4. Test entire user journey (free → buy → unlock)

---

## CRITICAL REMINDERS

1. **Reputation is everything** - First reviews stick forever in aviation communities
2. **Quality > Speed** - Better to launch in 3 weeks with amazing product than 1 week with mediocre
3. **Scenarios are the moat** - Basic Q&A is a commodity, scenarios are defensible
4. **Get CFI validation** - You're a student pilot; regulatory accuracy matters
5. **Netlify migration is URGENT** - GitHub Pages TOS violation could kill launch
6. **Single URL is non-negotiable** - Two URLs is unprofessional for this market
7. **Test license key flow extensively** - Broken unlock = instant refunds

---

## CONTACT & RESOURCES

**User Profile:**
- Student pilot working toward PPL
- Data analytics background (e-commerce startup)
- Systematic, validation-first approach
- Values authentic marketing
- Owns German Shepherd (not relevant but noted)

**FAA Resources for Question Writing:**
- 14 CFR (Federal Aviation Regulations): https://www.ecfr.gov/current/title-14
- AIM (Aeronautical Information Manual): https://www.faa.gov/air_traffic/publications/
- PHAK (Pilot's Handbook): https://www.faa.gov/regulations_policies/handbooks_manuals/aviation/phak
- ACS (Airman Certification Standards): https://www.faa.gov/training_testing/testing/acs/

**Tools Mentioned:**
- Netlify: Static hosting (free tier)
- Gumroad: Payment processing + license keys
- Plausible Analytics: Privacy-friendly analytics ($9/mo)
- Namecheap: Domain registrar (already purchased)

---

END OF SUMMARY
