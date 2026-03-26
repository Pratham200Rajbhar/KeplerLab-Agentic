'use client';

import { useRouter } from 'next/navigation';
import { Layers } from 'lucide-react';

export default function LandingPage() {
  const router = useRouter();

  return (
    <div className="dark bg-stitch-background text-stitch-on-background selection:bg-stitch-primary/30 min-h-screen">
      {/* Animated Background */}
      <div className="stitch-bg-animate">
        <div className="stitch-blob" style={{ top: '-10%', left: '-10%' }}></div>
        <div className="stitch-blob" style={{ bottom: '-10%', right: '-10%', animationDelay: '-5s' }}></div>
      </div>

      {/* Top Navigation Bar */}
      <nav className="fixed top-0 w-full z-50 bg-stitch-surface/70 backdrop-blur-xl border-b border-stitch-outline-variant/30">
        <div className="flex justify-between items-center px-6 py-4 max-w-7xl mx-auto">
          <div className="text-xl font-bold tracking-tight text-white font-headline flex items-center gap-2">
            <span className="material-symbols-outlined text-stitch-primary">orbit</span>
            KeplerLab AI Notebook
          </div>
          <button 
            onClick={() => router.push('/auth')}
            className="bg-stitch-primary hover:bg-stitch-secondary text-stitch-surface font-bold px-6 py-2 rounded-xl active:scale-95 transition-all shadow-lg shadow-stitch-primary/20"
          >
            Get Started
          </button>
        </div>
      </nav>

      <main className="pt-24">
        {/* Hero Section */}
        <section className="relative px-6 py-20 lg:py-32 max-w-7xl mx-auto overflow-hidden">
          <div className="relative z-10 flex flex-col items-center text-center">
            <span className="inline-block px-4 py-1.5 mb-6 text-xs font-bold tracking-widest uppercase rounded-full bg-stitch-surface-container-high border border-stitch-primary/20 text-stitch-primary">
              Next-Gen Knowledge Canvas
            </span>
            <h1 className="text-5xl lg:text-7xl font-extrabold tracking-tight mb-8 max-w-4xl font-headline leading-[1.1] text-white">
              Your Ideas, Enhanced by <span className="bg-clip-text text-transparent bg-gradient-to-r from-stitch-primary to-stitch-secondary">Universal Intelligence.</span>
            </h1>
            <p className="text-lg lg:text-xl text-stitch-on-surface-variant/80 max-w-2xl mb-12 leading-relaxed">
              KeplerLab is an advanced AI notebook workspace that transforms your multi-modal data into structured knowledge, creative assets, and automated workflows.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              <button 
                onClick={() => router.push('/auth')}
                className="bg-stitch-primary text-stitch-surface px-8 py-4 rounded-xl font-bold text-lg shadow-xl shadow-stitch-primary/20 hover:shadow-stitch-primary/40 transition-all"
              >
                Get Started for Free
              </button>
              <button className="px-8 py-4 rounded-xl font-bold text-lg border border-stitch-outline-variant hover:bg-stitch-surface-container-high transition-colors text-white">
                Watch Demo
              </button>
            </div>
          </div>

          {/* Dashboard Preview (Product Preview) */}
          <div className="mt-24 relative rounded-2xl border border-stitch-primary/10 bg-stitch-surface-container-low p-2 shadow-2xl overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-br from-stitch-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div className="rounded-xl overflow-hidden bg-stitch-surface-container-low border border-stitch-outline-variant/30 aspect-video flex">
              {/* Sidebar Mockup */}
              <div className="w-64 bg-stitch-surface-container hidden md:flex flex-col p-4 gap-4 border-r border-stitch-outline-variant/30">
                <div className="h-8 w-32 bg-stitch-primary/10 rounded-lg mb-4"></div>
                <div className="space-y-3">
                  <div className="h-4 w-full bg-stitch-primary/5 rounded"></div>
                  <div className="h-4 w-4/5 bg-stitch-primary/5 rounded"></div>
                  <div className="h-4 w-5/6 bg-stitch-primary/5 rounded"></div>
                </div>
              </div>
              {/* Main Canvas Mockup */}
              <div className="flex-1 p-6 flex flex-col gap-6">
                <div className="flex justify-between items-center">
                  <div className="h-6 w-48 bg-stitch-primary/10 rounded"></div>
                  <div className="flex gap-2">
                    <div className="h-8 w-8 bg-stitch-primary/10 rounded-full"></div>
                    <div className="h-8 w-8 bg-stitch-primary/10 rounded-full"></div>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-6 flex-1">
                  <div className="col-span-2 space-y-4">
                    <div className="h-32 w-full stitch-glass-card rounded-xl"></div>
                    <div className="h-64 w-full stitch-glass-card rounded-xl"></div>
                  </div>
                  <div className="space-y-4">
                    <div className="h-full w-full stitch-glass-card rounded-xl"></div>
                  </div>
                </div>
              </div>
            </div>
            <div className="absolute -bottom-6 -right-6 w-32 h-32 bg-stitch-primary/20 blur-3xl"></div>
          </div>
        </section>

        {/* About Section */}
        <section className="py-24 px-6 bg-stitch-surface-container-low/50 relative border-y border-stitch-outline-variant/10" id="about">
          <div className="max-w-7xl mx-auto grid lg:grid-cols-2 gap-16 items-center">
            <div>
              <h2 className="text-4xl font-bold mb-8 font-headline leading-tight text-white">
                A Notebook Built for <br /> <span className="text-stitch-primary">Infinite Context.</span>
              </h2>
              <p className="text-stitch-on-surface-variant/80 text-lg mb-10 leading-relaxed">
                Ditch the fragmented tools. KeplerLab integrates your entire research lifecycle. Upload PDFs, long-form videos, web URLs, or plain text. Our engine processes them in the background, making every detail searchable and actionable.
              </p>
              <div className="space-y-6">
                <div className="flex gap-4">
                  <div className="w-12 h-12 rounded-xl bg-stitch-primary/10 flex items-center justify-center shrink-0 border border-stitch-primary/20">
                    <span className="material-symbols-outlined text-stitch-primary">upload_file</span>
                  </div>
                  <div>
                    <h4 className="font-bold text-lg mb-1 text-white">Multi-Modal Ingestion</h4>
                    <p className="text-stitch-on-surface-variant/70 text-sm">Upload videos, URLs, and files. We transcribe and index everything instantly.</p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="w-12 h-12 rounded-xl bg-stitch-primary/10 flex items-center justify-center shrink-0 border border-stitch-primary/20">
                    <span className="material-symbols-outlined text-stitch-primary">smart_toy</span>
                  </div>
                  <div>
                    <h4 className="font-bold text-lg mb-1 text-white">Agent-Driven Synthesis</h4>
                    <p className="text-stitch-on-surface-variant/70 text-sm">Deploy AI agents to cross-reference your notes and generate summaries.</p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="w-12 h-12 rounded-xl bg-stitch-primary/10 flex items-center justify-center shrink-0 border border-stitch-primary/20">
                    <span className="material-symbols-outlined text-stitch-primary">movie</span>
                  </div>
                  <div>
                    <h4 className="font-bold text-lg mb-1 text-white">Media Generation</h4>
                    <p className="text-stitch-on-surface-variant/70 text-sm">Turn research into presentations, podcasts, or videos with one click.</p>
                  </div>
                </div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-4">
                <img alt="Abstract data nodes" className="rounded-2xl h-64 w-full object-cover border border-stitch-primary/20" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCedGa4kgMh6hi6cQ_znrO9ypIhZh80Rn0Gs3-Y7IDcdyRhBbMncHZSQPDwSCHKgQ0g9nrWOPxZjApj5dTYv-rSWES4Qv1aa7FuxtuHty9q-RmD6is7dijA9jGpod0hOJr9OFTnAtpEgi1NzAJKglDJWgqoGORAAEuHnQbZf2kI4hjacsxhcX6veK0lq1t9LE193mhcUVN6fwjOOO9DEGbouQz6zXyuhhbcHhpIEPVx5BqwvYP-GaI_zsgCQ0GBXRWl-nXHXsRwk4w" />
                <img alt="Sleek wave pattern" className="rounded-2xl h-48 w-full object-cover border border-stitch-primary/20" src="https://lh3.googleusercontent.com/aida-public/AB6AXuC0ySRIayPWYbuL0r61U3akXaND0IOlfcu_HXHZaCEdwmABagTrKOnK8zLJ3SznSG4Uy1UiL3wJx8Nd4SL5cGyYzsoz0Cx9q5fJmilxh3ECa0hyS1ziIlzmfHJImcEEYFGlVfBBeCTWM2cyL87ABLCvZaiCCwwLhU16hBRLg5qoKavwMwkdjOWiyShW_35OLQMyib3QAdn1lK7NqD46AfirEN4fm-9seltE-hY7aPqK26v3EEpk9Vi-U6GaXAe4pTMfs01aBlNDZNA" />
              </div>
              <div className="pt-12 space-y-4">
                <img alt="Global networks" className="rounded-2xl h-48 w-full object-cover border border-stitch-primary/20" src="https://lh3.googleusercontent.com/aida-public/AB6AXuC6wwKpMqtydYJBTCAxp2gY-3ErkcPyA9We2WYzdJeTX_CQANn8IqxY2cJSXg8V2D9KCtH33KJA27JrSHbosn-6UmizO8A6E7mJTmfsWAqb9d0QM9pdRbMn5okvk9Yqt6buuJxiznpjj8PX8tQEIOQbhBuToegft1PMi4HFIKWiTxanNs5D0Bd83tek_1cDqlucYKcra_rQ-V6m_j5NzcgaXfb1xDCz2vnygTCNRX1B10jGnTTZQ3_otrBL-6Uc_OEr8Mv0aOPQwbk" />
                <img alt="Tech interface" className="rounded-2xl h-64 w-full object-cover border border-stitch-primary/20" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDz4ysreUOsQkk9mJVQURpGQm-RzvvJjO_pXGOnTADnC9YlNj2PpJfOvou99yc7BXnXX2tdbPr2LCYu-pn-IiZWlMHH-4UboxPhuSO1MgC23a59Db8XvuVgy-pIVWBkUXTcvtnj-DFVYW4qzxd_mH3CJCSdtmsioeX_V0ClLs537peS2w07AEdUNQzkuaUoay_FRKbCcku1w5s-inFVYrzUdDem1n61CgN_D7lnxXU63U-tr9a9Y4QPW8h0O4z1t4lT1_bRme8bHy4" />
              </div>
            </div>
          </div>
        </section>

        {/* Features Bento Grid */}
        <section className="py-24 px-6 max-w-7xl mx-auto" id="features">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold font-headline mb-4 text-white">Precision Tools for Modern Minds</h2>
            <p className="text-stitch-on-surface-variant/80 max-w-2xl mx-auto">A unified suite of AI-native features designed to eliminate the friction between thought and execution.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {/* Large Feature */}
            <div className="md:col-span-2 stitch-glass-card p-8 rounded-2xl hover:bg-stitch-surface-container-high transition-all group border border-stitch-primary/10">
              <span className="material-symbols-outlined text-stitch-primary text-4xl mb-6">forum</span>
              <h3 className="text-2xl font-bold mb-3 font-headline text-white">Advanced AI Chat</h3>
              <p className="text-stitch-on-surface-variant/70 mb-6">Experience fluid conversation with full context awareness of your entire notebook library.</p>
              <div className="h-32 bg-stitch-surface-container-low rounded-xl p-4 overflow-hidden border border-stitch-outline-variant/30">
                <div className="h-2 bg-stitch-primary/20 rounded mb-2 w-3/4"></div>
                <div className="h-2 bg-stitch-primary/20 rounded mb-4 w-1/2"></div>
                <div className="w-full h-2 bg-stitch-secondary/10 rounded mb-2"></div>
                <div className="h-2 bg-stitch-secondary/10 rounded mb-2 w-2/3"></div>
              </div>
            </div>
            {/* Studio Card */}
            <div className="stitch-glass-card p-8 rounded-2xl hover:bg-stitch-surface-container-high transition-all border border-stitch-primary/10">
              <span className="material-symbols-outlined text-stitch-primary text-3xl mb-6">mic_external_on</span>
              <h3 className="text-xl font-bold mb-2 font-headline text-white">Podcast Studio</h3>
              <p className="text-stitch-on-surface-variant/70 text-sm">Generate conversational audio discussions from your research papers automatically.</p>
            </div>
            <div className="stitch-glass-card p-8 rounded-2xl hover:bg-stitch-surface-container-high transition-all border border-stitch-primary/10">
              <span className="material-symbols-outlined text-stitch-primary text-3xl mb-6">auto_awesome_motion</span>
              <h3 className="text-xl font-bold mb-2 font-headline text-white">Presentation Gen</h3>
              <p className="text-stitch-on-surface-variant/70 text-sm">Slide decks crafted by AI, populated with your unique data and insights.</p>
            </div>
            {/* Secondary Row */}
            <div className="stitch-glass-card p-6 rounded-2xl border border-stitch-primary/5">
              <span className="material-symbols-outlined text-stitch-secondary mb-4">terminal</span>
              <h4 className="font-bold mb-2 text-white">Code Execution</h4>
              <p className="text-stitch-on-surface-variant/70 text-xs">Run Python snippets directly inside your notes for live data analysis.</p>
            </div>
            <div className="stitch-glass-card p-6 rounded-2xl border border-stitch-primary/5">
              <span className="material-symbols-outlined text-stitch-secondary mb-4">account_tree</span>
              <h4 className="font-bold mb-2 text-white">Knowledge Graph</h4>
              <p className="text-stitch-on-surface-variant/70 text-xs">Visualize how your concepts connect across different sources.</p>
            </div>
            <div className="stitch-glass-card p-6 rounded-2xl border border-stitch-primary/5">
              <span className="material-symbols-outlined text-stitch-secondary mb-4">bolt</span>
              <h4 className="font-bold mb-2 text-white">Agent Mode</h4>
              <p className="text-stitch-on-surface-variant/70 text-xs">Autonomous agents that perform deep research and verify facts for you.</p>
            </div>
            <div className="stitch-glass-card p-6 rounded-2xl border border-stitch-primary/5">
              <span className="material-symbols-outlined text-stitch-secondary mb-4">quiz</span>
              <h4 className="font-bold mb-2 text-white">Quizzes & Cards</h4>
              <p className="text-stitch-on-surface-variant/70 text-xs">Transform any note into an interactive learning experience instantly.</p>
            </div>
          </div>
        </section>

        {/* Workflow Section (How it Works) */}
        <section className="py-24 px-6 bg-stitch-surface-container-low/30 overflow-hidden relative border-t border-stitch-outline-variant/10" id="workflow">
          <div className="max-w-7xl mx-auto">
            <div className="flex flex-col md:flex-row justify-between items-end mb-16 gap-8">
              <div className="max-w-xl">
                <h2 className="text-4xl font-bold font-headline mb-6 text-white">From Data to <span className="text-stitch-primary">Delivered.</span></h2>
                <p className="text-stitch-on-surface-variant/80 text-lg">A linear, intuitive process that takes you from raw inputs to polished final outputs in minutes.</p>
              </div>
              <div className="h-1 bg-stitch-primary/10 flex-1 mx-8 mb-4 hidden md:block"></div>
            </div>
            <div className="grid md:grid-cols-5 gap-8 relative">
              {/* Step 1 */}
              <div className="flex flex-col gap-4 group">
                <div className="text-6xl font-black text-stitch-primary/10 font-headline group-hover:text-stitch-primary/20 transition-colors">01</div>
                <h4 className="font-bold text-xl text-white">Upload</h4>
                <p className="text-stitch-on-surface-variant/70 text-sm">Drag in PDFs, paste URLs, or upload MP4s.</p>
              </div>
              {/* Step 2 */}
              <div className="flex flex-col gap-4 group">
                <div className="text-6xl font-black text-stitch-primary/10 font-headline group-hover:text-stitch-primary/20 transition-colors">02</div>
                <h4 className="font-bold text-xl text-white">Process</h4>
                <p className="text-stitch-on-surface-variant/70 text-sm">AI transcribes, indexes, and extracts key entities.</p>
              </div>
              {/* Step 3 */}
              <div className="flex flex-col gap-4 group">
                <div className="text-6xl font-black text-stitch-primary/10 font-headline group-hover:text-stitch-primary/20 transition-colors">03</div>
                <h4 className="font-bold text-xl text-white">Chat</h4>
                <p className="text-stitch-on-surface-variant/70 text-sm">Query your documents with natural language.</p>
              </div>
              {/* Step 4 */}
              <div className="flex flex-col gap-4 group">
                <div className="text-6xl font-black text-stitch-primary/10 font-headline group-hover:text-stitch-primary/20 transition-colors">04</div>
                <h4 className="font-bold text-xl text-white">Generate</h4>
                <p className="text-stitch-on-surface-variant/70 text-sm">Create studio-quality assets from your workspace.</p>
              </div>
              {/* Step 5 */}
              <div className="flex flex-col gap-4 group">
                <div className="text-6xl font-black text-stitch-primary/10 font-headline group-hover:text-stitch-primary/20 transition-colors">05</div>
                <h4 className="font-bold text-xl text-white">Export</h4>
                <p className="text-stitch-on-surface-variant/70 text-sm">Publish to web or export in various formats.</p>
              </div>
            </div>
          </div>
        </section>

        {/* Why KeplerLab Section */}
        <section className="py-24 px-6 max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-20 items-center">
            <div className="order-2 lg:order-1">
              <div className="relative rounded-2xl overflow-hidden shadow-2xl border border-stitch-primary/20 group">
                <img alt="Laptop in green lighting" className="w-full aspect-square object-cover transition-transform duration-700 group-hover:scale-105" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCMmU2dr4_BJ47NRBt2EbyXiNkLgnWorl5SYRKoYhwqQ34Sz1TM1o-0daFL7zS_fzxZDxxt3m5Pr8qJPRnER04xKlknvtOiUNbCCeuiu0K9gRBNkYvJdlsWVvzhAHhUhzz_R_bXhBi0ZUikTOoSeNmg1zaKK1BNqCSUkUDim-Wdmp9DhsGAf1VY7JrVxppyRWEAu9RMluzYo1S3Nj5FYZCyvuarQtduVVZ9aaYA7Qj4GJBHeH1B364mvuuPYjc8z7biwWgxcIjESVI" />
                <div className="absolute inset-0 bg-gradient-to-t from-stitch-background via-transparent to-transparent"></div>
              </div>
            </div>
            <div className="order-1 lg:order-2">
              <h2 className="text-4xl font-bold font-headline mb-8 text-white">Why Intelligence Prefers <span className="text-stitch-primary">KeplerLab</span></h2>
              <ul className="space-y-8">
                <li className="flex gap-6">
                  <span className="material-symbols-outlined text-stitch-primary text-3xl">verified_user</span>
                  <div>
                    <h4 className="font-bold text-xl mb-2 text-white">Secure Retrieval</h4>
                    <p className="text-stitch-on-surface-variant/70">Your data is yours. We use private vector stores to ensure your intellectual property never leaves your environment.</p>
                  </div>
                </li>
                <li className="flex gap-6">
                  <span className="material-symbols-outlined text-stitch-primary text-3xl">stream</span>
                  <div>
                    <h4 className="font-bold text-xl mb-2 text-white">Real-Time Streaming</h4>
                    <p className="text-stitch-on-surface-variant/70">No more waiting. Watch AI responses and processing tasks happen in real-time as you work.</p>
                  </div>
                </li>
                <li className="flex gap-6">
                  <span className="material-symbols-outlined text-stitch-primary text-3xl">cloud_sync</span>
                  <div>
                    <h4 className="font-bold text-xl mb-2 text-white">Background Resilience</h4>
                    <p className="text-stitch-on-surface-variant/70">Long-running synthesis jobs run in the background. Close the tab, we'll notify you when it's done.</p>
                  </div>
                </li>
              </ul>
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section className="py-24 px-6">
          <div className="max-w-5xl mx-auto stitch-glass-card p-12 lg:p-20 rounded-[2rem] border border-stitch-primary/20 relative overflow-hidden text-center">
            <div className="absolute top-0 right-0 w-64 h-64 bg-stitch-primary/5 blur-[100px] rounded-full"></div>
            <div className="absolute bottom-0 left-0 w-64 h-64 bg-stitch-primary/5 blur-[100px] rounded-full"></div>
            <h2 className="text-4xl lg:text-6xl font-bold font-headline mb-8 relative z-10 text-white">Start using KeplerLab AI Notebook</h2>
            <p className="text-stitch-on-surface-variant/80 text-lg lg:text-xl mb-12 max-w-2xl mx-auto relative z-10">Join thousands of researchers, students, and creators building the future of knowledge work.</p>
            <div className="flex justify-center relative z-10">
              <button 
                onClick={() => router.push('/auth')}
                className="bg-stitch-primary hover:bg-stitch-secondary text-stitch-surface font-bold px-12 py-5 rounded-xl text-xl hover:shadow-2xl hover:shadow-stitch-primary/30 transition-all active:scale-95"
              >
                Get Started
              </button>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="bg-stitch-surface-container-low w-full py-12 border-t border-stitch-outline-variant/30">
        <div className="flex flex-col md:flex-row justify-between items-center px-8 max-w-7xl mx-auto gap-4">
          <div className="flex flex-col items-center md:items-start gap-2">
            <div className="text-lg font-bold text-white font-headline flex items-center gap-2">
              <span className="material-symbols-outlined text-stitch-primary text-sm">orbit</span>
              KeplerLab AI
            </div>
            <div className="text-stitch-on-surface-variant/50 text-sm">© 2024 KeplerLab AI. All rights reserved.</div>
          </div>
          <div className="flex gap-8">
            <a className="text-stitch-on-surface-variant/50 hover:text-stitch-primary transition-colors text-sm" href="#">Privacy Policy</a>
            <a className="text-stitch-on-surface-variant/50 hover:text-stitch-primary transition-colors text-sm" href="#">Terms of Service</a>
          </div>
          <div className="flex gap-6">
            <a className="text-stitch-on-surface-variant/50 hover:text-stitch-primary opacity-80 hover:opacity-100 transition-all" href="#">
              <svg className="w-5 h-5 fill-current" viewBox="0 0 24 24"><path d="M24 4.557c-.883.392-1.832.656-2.828.775 1.017-.609 1.798-1.574 2.165-2.724-.951.564-2.005.974-3.127 1.195-.897-.957-2.178-1.555-3.594-1.555-3.179 0-5.515 2.966-4.797 6.045-4.091-.205-7.719-2.165-10.148-5.144-1.29 2.213-.669 5.108 1.523 6.574-.806-.026-1.566-.247-2.229-.616-.054 2.281 1.581 4.415 3.949 4.89-.693.188-1.452.232-2.224.084.626 1.956 2.444 3.379 4.6 3.419-2.07 1.623-4.678 2.348-7.29 2.04 2.179 1.397 4.768 2.212 7.548 2.212 9.142 0 14.307-7.721 13.995-14.646.962-.695 1.797-1.562 2.457-2.549z"></path></svg>
            </a>
            <a className="text-stitch-on-surface-variant/50 hover:text-stitch-primary opacity-80 hover:opacity-100 transition-all" href="#">
              <svg className="w-5 h-5 fill-current" viewBox="0 0 24 24"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.041-1.416-4.041-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"></path></svg>
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
