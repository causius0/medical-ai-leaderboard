import Link from 'next/link';

export default function ProjectPage() {
    return (
        <div className="min-h-screen bg-gray-50 p-6 md:p-8">
            <div className="max-w-4xl mx-auto">
                <header className="mb-12 flex justify-between items-center">
                    <div>
                        <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-2 font-serif">
                            About the Project
                        </h1>
                        <p className="text-lg text-gray-600">
                            Evaluating Medical Intelligence at Scale
                        </p>
                    </div>
                    <Link
                        href="/"
                        className="px-6 py-2 bg-white border border-gray-200 rounded-full shadow-sm hover:shadow-md transition-all text-gray-700 font-medium"
                    >
                        ← Back
                    </Link>
                </header>

                <main className="space-y-8 bg-white p-8 md:p-12 rounded-2xl shadow-sm border border-gray-200">
                    <section className="space-y-6">
                        <p className="text-xl text-gray-800 leading-relaxed">
                            The Medical AI Leaderboard is the result of an international collaboration between over
                            <span className="font-semibold text-gray-900"> 20 medical doctors, AI engineers, and researchers</span>.
                        </p>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 my-10">
                            <div className="bg-blue-50 p-6 rounded-xl border border-blue-100">
                                <h3 className="text-blue-900 font-bold text-lg mb-2">10,000+ Questions</h3>
                                <p className="text-blue-800 text-sm">
                                    Extensive dataset assembled from medical licensing examinations across Europe.
                                </p>
                            </div>
                            <div className="bg-green-50 p-6 rounded-xl border border-green-100">
                                <h3 className="text-green-900 font-bold text-lg mb-2">Multi-National</h3>
                                <p className="text-green-800 text-sm">
                                    Data sourced from official sources in Italy, Spain, France, and Portugal.
                                </p>
                            </div>
                        </div>

                        <p className="text-gray-700 leading-relaxed">
                            This rigorous evaluation framework was developed to assess the true capabilities of clinical
                            reasoning in modern AI models. By leveraging actual licensing exam questions, we provide
                            a standardized benchmark that reflects the complexity of real-world medical knowledge.
                        </p>
                    </section>

                    <section className="pt-8 border-t border-gray-100">
                        <h2 className="text-2xl font-bold text-gray-900 mb-4">Recognition & Publication</h2>
                        <div className="bg-gray-50 p-6 rounded-xl border border-gray-200 flex flex-col md:flex-row items-center gap-6">
                            <div className="flex-shrink-0 bg-yellow-400 text-white p-4 rounded-lg shadow-inner">
                                <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                                </svg>
                            </div>
                            <div>
                                <p className="text-gray-900 font-semibold text-lg mb-1">Best Presentation Award</p>
                                <p className="text-gray-600 text-sm mb-3">
                                    Presented at <span className="font-medium">EurIPS</span> in December 2025.
                                </p>
                                <a
                                    href="https://multimodal-rep-learning-for-health.github.io/papers/11_Are_Large_Vision_Language_M.pdf"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center text-blue-600 font-medium hover:text-blue-800 transition-colors"
                                >
                                    Read the Publication
                                    <svg className="ml-2 w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                    </svg>
                                </a>
                            </div>
                        </div>
                    </section>
                </main>

                <footer className="mt-20 pt-8 border-t border-gray-200 text-center text-sm text-gray-500">
                    © {new Date().getFullYear()} Medical AI Leaderboard. All rights reserved.
                </footer>
            </div>
        </div>
    );
}
