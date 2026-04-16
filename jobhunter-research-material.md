# Open-source job hunting automation: a complete pipeline inventory

**Over 50 open-source repositories and tools exist today that can be assembled into a fully automated job hunting pipeline** — from scraping listings across 10+ boards, through AI-powered resume tailoring, to auto-applying and tracking outcomes. The ecosystem is surprisingly mature: the top project (AIHawk) has nearly 30,000 GitHub stars, and production-ready libraries like JobSpy can scrape LinkedIn, Indeed, and Glassdoor in a single function call. Combined with free job board APIs (RemoteOK, Adzuna, Arbeitnow), ATS-optimized resume generators, and AI agent frameworks, a Laravel 12 + Vue 3 admin panel can orchestrate the entire pipeline through Python microservices communicating via REST APIs or message queues.

---

## Job scraping: JobSpy dominates with 8+ boards in one library

The scraping landscape has consolidated around a few high-quality Python libraries that can serve as microservices behind a Laravel backend.

### Tier 1: Production-ready scrapers

**JobSpy** (`speedyapply/JobSpy`) is the clear winner with **~3,100 stars** and active maintenance (v1.1.82, commits ongoing through 2026). It scrapes **LinkedIn, Indeed, Glassdoor, Google Jobs, ZipRecruiter, Bayt, Naukri, and BDJobs** simultaneously via a single `scrape_jobs()` call. Built on BeautifulSoup and httpx, it returns pandas DataFrames exportable to CSV/JSON/Excel. Key features include proxy rotation (including SOCKS5), remote-only filtering, job type filters, and full description fetching. Install is simply `pip install python-jobspy`. Two FastAPI Docker wrappers already exist — **rainmanjam/jobspy-api** and **REVERSEDCD/jobspy-api** — providing versioned REST endpoints with API key auth and rate limiting, ready for Laravel integration.

**linkedin-api** (`tomquirk/linkedin-api`, **~2,000+ stars**) provides direct access to LinkedIn's internal Voyager API without browser automation — pure HTTP requests supporting job search, profile lookup, and messaging. It offers advanced filters (keywords, experience level, remote, company, industry) but explicitly violates LinkedIn's ToS Section 8.2 and risks account bans. **linkedin_scraper** (`joeyism/linkedin_scraper`, **~3,900 stars**) takes the browser automation route via Playwright, supporting profile, company, and job scraping with session persistence.

### Tier 2: Specialized and niche scrapers

**JobFunnel** (`PaulMcInnis/JobFunnel`, **~2,100 stars**) was a beloved tool that maintained a master CSV with deduplication and status tracking across Indeed and Glassdoor, but it was **archived in December 2025**. Its architecture — YAML config, crontab scheduling, extensible base scrapers — remains a useful reference. **ai-job-scraper** (`BjornMelin/ai-job-scraper`) adds an AI layer using local LLMs (Qwen3-4B) via ScrapeGraph-AI for relevance filtering, with a Streamlit dashboard and SQLite full-text search. For Wellfound/AngelList, `jwc20/wellfound-scraper` provides a basic Python scraper using the platform's internal API, while `Radeance/wellfound-jobs-scraper-public` offers a production-grade Apify actor processing thousands of jobs. For Indeed specifically, `dennisvdang/indeed-job-scraper` uses Selenium with undetected-chromedriver and CAPTCHA pause handling.

### Legal job board APIs eliminate scraping risk entirely

A combination of four free APIs provides legal access to tens of thousands of listings:

| API | Free tier | Coverage | Key advantage |
|-----|-----------|----------|---------------|
| **RemoteOK** (`remoteok.com/api`) | Fully free, no auth | 30,000+ remote jobs globally | Public JSON endpoint, ~170ms response |
| **Adzuna** (`api.adzuna.com`) | Free with registration | 11+ countries, aggregated | Salary data, company reviews, categories |
| **Arbeitnow** (`arbeitnow.com/api`) | Free public API | Europe + remote, ATS-sourced | Filters: remote, visa sponsorship |
| **Jobicy** (`jobicy.com/api/v2`) | Free (50 jobs/call) | Remote across industries | Geo and industry filtering, RSS feed |
| **JSearch** (RapidAPI) | Freemium | Google for Jobs aggregator (500+ sites) | 30+ data points, includes LinkedIn/Indeed |
| **Fantastic.jobs** | Paid | 200K+ jobs/month from ATS platforms | Greenhouse, Lever, Workday sourced |

**For the target pipeline**, the recommended architecture is a FastAPI microservice exposing endpoints for each source — `/scrape/jobspy` for multi-board scraping, `/api/remoteok`, `/api/adzuna`, etc. — with an `/aggregate` endpoint that combines and deduplicates results. Laravel calls these endpoints via its `Http` facade or dispatches jobs to a Redis/RabbitMQ queue for async processing.

---

## AI resume tailoring: from 35K-star builders to LLM-powered customizers

The resume tooling ecosystem spans three categories: visual builders, AI tailoring engines, and ATS analysis tools.

### Visual resume builders (self-hostable)

**Reactive Resume** (`AmruthPillai/Reactive-Resume`, **~35,600 stars**) is the most popular open-source resume builder. Built on NestJS + React + PostgreSQL with Docker Compose deployment, it offers dozens of templates, drag-and-drop editing, OpenAI integration for writing enhancement, OAuth authentication, and shareable resume links with analytics. Its REST API makes it integratable with external systems, and self-hosting ensures full data control. **OpenResume** (`xitanggg/open-resume`, **~8,500 stars**) takes a client-side approach — a Next.js app that runs entirely in the browser with zero backend, featuring ATS-friendly formatting tested against Greenhouse and Lever, plus a resume parser for import. **RenderCV** (`rendercv/rendercv`, **~3,700 stars**) targets engineers and academics with YAML-to-PDF generation via Typst, offering CLI, Docker, and web interfaces with AI chat polishing.

### AI-powered resume tailoring (the critical differentiator)

**Resume Matcher** (`srbhr/Resume-Matcher`, **~26,200 stars**) is the leading ATS analysis tool. It uses NLP (TF-IDF, cosine similarity, vector embeddings via Qdrant) to score resumes against job descriptions, extract missing keywords, and suggest improvements. While it doesn't generate resumes, it's essential as a scoring/validation step in any pipeline. It includes a "master resume" concept where a comprehensive resume feeds into tailored versions.

**ResumeLM** (`olyaiy/resume-lm`, **232 stars**, 856 commits) is the most feature-complete AI-powered tailoring tool found. It supports **multiple LLM backends — GPT, Claude, Gemini, DeepSeek, and Groq** — and implements a two-tier system of base resumes plus per-job tailored versions. Built on Next.js 15 + Supabase, it includes ATS scoring, keyword optimization insights, cover letter generation, and application tracking. Self-hostable via Docker.

**ResumeFlow/zlm** (`Ztrimus/ResumeFlow`, **~200 stars**) takes a streamlined approach: input a job URL and master resume, and it generates a tailored resume plus cover letter as LaTeX-formatted PDFs. Available as a pip package (`zlm`), Streamlit app, and CLI — ideal for automation. **resume-ai** (`resume-llm/resume-ai`, **363 stars**) is the privacy-first option, using local LLMs via Ollama to generate ATS-ready DOCX files through Pandoc, with a built-in Kanban tracker. For the JSON Resume ecosystem, **resume-optimizer** (`panasenco/resume-optimizer`) takes the standard JSON Resume format plus a job description and rewrites work highlights with ATS keywords via OpenAI.

### Multi-agent AI approaches

Several projects use **CrewAI** to orchestrate specialized agents — a Job Analyzer, CV Customizer, and Cover Letter Writer working in sequence. Notable implementations include `drukpa1455/crewai-job`, `tonykipkemboi/resume-optimization-crew` (with match scoring and interview prep), and `peshak2008/crewai_resumesummary_coverletter_generator` (which scrapes Indeed JDs and tracks applications in Notion). These demonstrate the emerging pattern of **agentic job application workflows** where multiple AI agents collaborate on different aspects of the application.

---

## ATS optimization: what actually matters for passing the filters

**97% of Fortune 500 companies** use Applicant Tracking Systems. The most common platforms are Workday (large enterprise), Greenhouse (tech/startups), Lever (mid-market tech), Taleo/Oracle (legacy enterprise), and iCIMS (large employers). Understanding their parsing rules is essential for any automated resume generator.

ATS parsing follows a three-step process: text extraction via OCR/NLP, keyword matching against the job description, and scoring/ranking (typically 0-100, with **80+** needed to pass to a recruiter). The scoring weights approximately **40-50% on keyword density**, 25-30% on format parseability, and 20-25% on section completeness.

The formatting rules that matter most: use a **single-column layout** (multi-column confuses parsers), standard fonts (Arial, Calibri, 10-12pt), standard section headers ("Work Experience" not "Career Journey"), reverse chronological order, and .docx or text-based PDF format. Critical failures include tables, text boxes, graphics, skill bars, images, headers/footers containing contact info, and inconsistent date formats. **Match 70-80% of job description keywords**, include both full terms and acronyms ("Search Engine Optimization (SEO)"), and integrate keywords into achievement context rather than generic lists. White-text keyword stuffing is detected and flagged as spam by modern ATS systems.

---

## End-to-end automation: AIHawk leads with 30K stars

### The dominant platform

**Jobs_Applier_AI_Agent_AIHawk** (`feder-cr/Jobs_Applier_AI_Agent_AIHawk`, **~29,700 stars**, 4,500 forks) is the most popular end-to-end job automation project on GitHub, featured in Business Insider, TechCrunch, and The Verge. Built in Python with Selenium, it automates LinkedIn job applications at scale with AI-powered form filling, personalized resume generation, and intelligent question answering via OpenAI, Ollama, or Gemini. Configuration is YAML-based, covering job preferences, skills, and experience. The original creator has partially commercialized the project, but an **active community fork** (`Intusar/Auto_Jobs_Applier_AI_Agent`, 309 commits) continues open-source development. It covers scraping, tailoring, applying, and basic tracking — the most complete single repository found.

### Strong alternatives by platform

**Auto_job_applier_linkedIn** (`GodsScion`, **~1,900 stars**) offers robust LinkedIn Easy Apply automation with AI question answering and resume customization based on extracted job skills. **EasyApplyJobsBot** (`wodsuz`, **~3,400 stars**) supports the widest platform range — LinkedIn, Glassdoor, AngelCo, Greenhouse, Monster, GlobalLogic, and Djinni — with a commercial Apllie.com dashboard companion for analytics. For freelance platforms, **Upwork-AI-jobs-applier** (`kaymen99`) uses LangChain with multi-LLM support (OpenAI, Claude, Gemini, Groq) in a Docker container, featuring intelligent job scoring with a 7/10 threshold and dynamic cover letter generation.

The most innovative entry is **JobHuntr** (`lookr-fyi/job-application-bot-by-ollama-ai`, **~397 stars**), an Electron desktop app using local LLMs via Ollama that covers LinkedIn, Indeed, ZipRecruiter, Glassdoor, and Dice. Its "D.A.M.N. Mode" runs headlessly, and it includes built-in features to DM hiring managers after applying. It runs inside the user's Chrome profile for stealth and keeps all AI processing on-device.

### Browser extensions for ATS form filling

A category of Chrome extensions targets the tedious ATS application forms:

- **AI-Job-Autofill** (`laynef/AI-Job-Autofill`) — supports Greenhouse, Lever, Workday, Ashby, BambooHR, Workable, Jobvite, SmartRecruiters with AI-powered autofill and cover letter generation
- **ApplyEase** (`sainikhil1605/ApplyEase`) — React + FastAPI extension with resume match scoring, local LLM support, and auto-tracking
- **job_app_filler** (`berellevy/job_app_filler`) — specializes in Workday and iCIMS forms using MutationObserver for dynamic fields
- **Autofill-Jobs** (`andrewmillercode/Autofill-Jobs`) — Vue.js extension for Greenhouse, Lever, Workday

### n8n workflow automations

The no-code approach via **n8n** has produced complete pipeline templates. **n8n-job-hacker** (`sirlifehacker`) implements the full cycle: scrape jobs via Apify → customize resume → extract hiring manager data via Apollo → generate personalized outreach emails via GPT → store in Notion → upload resume to Google Drive, processing 50-100 postings per run. **Job-Hunter** (`adarsh-ajay`) runs daily scheduled LinkedIn scraping with Gemini AI evaluation, auto-generated cover letters, and Telegram notifications.

---

## Application tracking: self-hosted CRMs for job seekers

**JobSync** (`Gsync/jobsync`, **~283-506 stars**) is the most capable open-source tracker — a Next.js + Prisma + PostgreSQL self-hosted app with AI resume review (via Ollama), job matching scores, Kanban boards, task management, time tracking, and analytics dashboards. It exposes REST API routes suitable for Laravel integration. **CareerSync** (`Tomiwajin/CareerSync`) takes a unique stateless approach, using ML models (SetFit classifier, T5-small) to automatically parse Gmail for application status updates with **95%+ classification accuracy** across 7 categories (Applied, Interview, Rejected, Offer, etc.) — zero manual tracking required.

**OpenCATS** (`opencats/OpenCATS`, **664 stars**) is a mature PHP/MySQL ATS designed for recruiters but adaptable for job seekers, handling 100K+ records with pipeline visualization and resume storage. For simpler needs, `machadop1407/job-application-tracker` provides a clean Next.js Kanban board with MongoDB and Clerk auth. The **resume-ai** project also includes a built-in Kanban board alongside its local LLM resume generation.

---

## Cold email tools and the strategy that yields 15-25% response rates

### Open-source cold email generators

**project-genai-cold-email-generator** (`codebasics`, **130 stars**) demonstrates the core pattern: Llama 3.1 via Groq Cloud + LangChain + ChromaDB extract job listings from career pages and generate personalized emails with relevant portfolio links. **ColdContactXLSX** (`aasthas2022`) is the most practical tool for batch outreach — it generates potential recruiter email addresses from name+company patterns and sends customized emails from Excel spreadsheets with automated follow-ups. **Email-automation** (`PaulleDemon`, **124 stars**) provides a Django-based platform with Jinja2 templates, scheduling, and configurable follow-up rules.

For AI-powered personalization at scale, **PocketFlow-Tutorial-Cold-Email-Personalization** (`The-Pocket`, 36 stars) generates personalized opening lines by web-searching each prospect from a CSV, while `manishpaneru/ColdEmailGenerator` combines resume PDF and job posting URL analysis to generate matched emails with selectable tones.

### What makes cold emails work for job seekers

Cold emails to hiring managers achieve **15-25% response rates** versus 2-5% for standard online applications. The optimal email is **75-150 words** with five components: a specific subject line under 10 words, a personalized opening referencing company news or the recipient's work, a value proposition with quantified results ("increased conversion by 35%"), one line of social proof, and a clear CTA asking for a conversation rather than a job. **Tuesday through Thursday at 8-10 AM** in the recipient's timezone yields the highest open and response rates. The follow-up sequence should be 3 total emails spaced 4-7 days apart, each adding new value.

For finding contacts, **Hunter.io** (50 free credits/month) and **Apollo.io** (224M+ verified contacts, free tier) are the leading tools. Most companies use predictable email patterns (firstname.lastname@company.com) — finding one employee's email reveals the pattern.

### Email deliverability requirements

**SPF, DKIM, and DMARC** authentication are non-negotiable — fully authenticated senders are **2.7x more likely to reach the inbox**. Use a separate domain for cold outreach (e.g., yourname-mail.com), warm it up over 2-4 weeks starting at 1 email/day and increasing by 2 daily, and stay well under provider limits (20-50 personalized emails/day for cold outreach). Plain text outperforms HTML, avoid spam trigger words, keep links to 1-2 maximum, and verify all addresses before sending to maintain bounce rates below 1%. Open-source warmup tools include `WKL-Sec/Warmer` (Python/Selenium) and `juselius/Warmup` (Docker). CAN-SPAM permits cold email with an opt-out mechanism and physical address; GDPR allows B2B outreach under "legitimate interest" with transparency requirements.

---

## LinkedIn scraping: legal but risky, with clear boundaries

The **hiQ Labs v. LinkedIn** saga established that scraping publicly available data does not violate the Computer Fraud and Abuse Act (CFAA) — the Ninth Circuit affirmed this twice (2019, 2022), and the Supreme Court's *Van Buren* decision reinforced that CFAA violations require accessing data behind an authorization barrier. However, LinkedIn's Terms of Service **are enforceable under breach of contract** — hiQ ultimately settled for $500K in damages and destruction of all scraped data. The **Meta v. Bright Data** ruling (January 2024) further clarified that if data is visible without authentication, scraping is harder to attack legally.

**Practical risk assessment**: scraping public LinkedIn job listings without login is low risk (unlikely CFAA violation); using an account to scrape carries medium risk (ToS breach, account ban); commercial scraping at scale with fake accounts creates high litigation risk from contract and tort claims. LinkedIn's official Job Posting API is **closed to new partners** — access requires being a LinkedIn Talent Solutions Partner (ATS/staffing agencies only). The safest alternative is using **JSearch via RapidAPI**, which aggregates Google for Jobs data including LinkedIn postings, or using JobSpy's guest-facing LinkedIn scraper with proxy rotation.

---

## Integration architecture for Laravel 12 + Vue 3

The recommended pattern uses **Python FastAPI microservices** behind a Laravel API gateway, communicating via two channels:

**REST API for synchronous operations**: Laravel's `Http::post('http://python-service:5000/scrape', $params)` facade calls FastAPI endpoints directly. This works well for job searches, resume scoring, and email generation where results return in seconds. Each Python service runs in its own Docker container on the shared Docker network.

**Message queues for async processing**: Laravel dispatches jobs to **Redis or RabbitMQ**, which Python workers consume for long-running tasks — bulk scraping, AI resume tailoring, batch email generation. Results write back to the shared PostgreSQL database or trigger webhooks to Laravel endpoints. Laravel's built-in queue system with the RabbitMQ driver handles this natively.

The Docker Compose architecture runs separate containers for the Laravel web app (PHP-FPM + Nginx), Python API services (FastAPI), PostgreSQL, Redis, and optionally RabbitMQ and an Ollama instance for local LLM inference. Services communicate via the Docker internal network using container names as hostnames. A Traefik or Nginx reverse proxy handles external routing. The Vue 3 frontend communicates exclusively with the Laravel API, which orchestrates all backend services.

---

## Recommended pipeline assembly from existing components

Assembling the optimal pipeline from the repositories found yields this architecture:

**Scraping layer**: JobSpy library wrapped in `rainmanjam/jobspy-api` (FastAPI + Docker) for LinkedIn, Indeed, Glassdoor, Google Jobs, ZipRecruiter. Supplement with RemoteOK, Adzuna, and Arbeitnow free APIs for legal coverage. Filter by keywords ("AI Agent", "AI Engineer", "Prompt Engineer", "Full Stack Developer") using JobSpy's `search_term` parameter and pandas DataFrame filtering.

**Resume tailoring layer**: Store the master resume in JSON Resume format. Use Resume Matcher for ATS scoring and keyword gap analysis. Feed gaps into ResumeLM or ResumeFlow for AI-powered rewriting via GPT/Claude/Gemini. Generate final output through RenderCV (YAML → PDF via Typst) or Reactive Resume's API for polished, ATS-compliant documents in DOCX/PDF.

**Application layer**: AIHawk's community fork for LinkedIn auto-apply with AI form filling. ApplyEase or AI-Job-Autofill browser extensions for Greenhouse, Lever, and Workday applications. Upwork-AI-jobs-applier for freelance platforms.

**Tracking layer**: JobSync as the self-hosted application tracker with Kanban boards and analytics. CareerSync for automated Gmail-based status detection. All data flows into the Laravel admin panel's PostgreSQL database.

**Outreach layer**: ColdContactXLSX for email discovery and batch sending. Project-genai-cold-email-generator's pattern for AI personalization. Email-automation for scheduling and follow-up sequences. SPF/DKIM/DMARC on a dedicated outreach domain with 2-4 week warmup.

## Conclusion

The open-source job hunting automation ecosystem has reached a level of maturity where a complete pipeline can be assembled without writing most components from scratch. **JobSpy + AIHawk + Resume Matcher + ResumeLM + JobSync** form the backbone — covering scraping, applying, scoring, tailoring, and tracking respectively. The critical insight is that legal job board APIs (RemoteOK, Adzuna, JSearch) should supplement scraping rather than relying entirely on fragile web scrapers, and that the JSON Resume standard provides the ideal data interchange format between components. The biggest remaining gap is the orchestration layer — connecting these tools into a unified workflow — which is precisely where a Laravel 12 + Vue 3 admin panel adds the most value, serving as the control plane that coordinates Python microservices via REST APIs and async queues while providing the user interface for configuration, monitoring, and manual intervention points.