import Link from 'next/link';

const teamMembers = [
  {
    name: 'Andrea Causio, MD',
    role: 'Project Lead (up to July 2025)',
    image: '/team/acausio.jpg',
    link: 'https://causio.xyz/',
  },
  {
    name: 'Dr. Sarah Mitchell',
    role: 'Principal Investigator & Clinical Lead',
    image: '/team/member1.png',
  },
  {
    name: 'Dr. Arthur Chen',
    role: 'Head of Medical Research & Strategy',
    image: '/team/member2.png',
  },
  {
    name: 'Elena Rodriguez',
    role: 'Lead Data Scientist & ML Engineer',
    image: '/team/member3.png',
  }
];

export default function TeamPage() {
  return (
    <div className="min-h-screen bg-gray-50 p-6 md:p-8">
      <div className="max-w-7xl mx-auto">
        <header className="mb-12 flex justify-between items-center">
          <div>
            <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-2">
              The Team
            </h1>
            <p className="text-lg text-gray-600">
              The experts behind the Medical AI Leaderboard
            </p>
          </div>
          <Link
            href="/"
            className="px-6 py-2 bg-white border border-gray-200 rounded-full shadow-sm hover:shadow-md transition-all text-gray-700 font-medium"
          >
            ← Back to Leaderboard
          </Link>
        </header>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {teamMembers.map((member, index) => (
            <div
              key={index}
              className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-lg transition-all duration-300 group max-w-[280px] mx-auto w-full"
            >
              <div className="aspect-square overflow-hidden bg-gray-100">
                <img
                  src={member.image}
                  alt={member.name}
                  className="w-full h-full object-cover object-top group-hover:scale-105 transition-transform duration-500"
                />
              </div>
              <div className="p-5">
                <h2 className="text-lg font-bold text-gray-900 mb-1 truncate">
                  {member.link ? (
                    <a
                      href={member.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 transition-colors underline decoration-blue-200 decoration-2 underline-offset-4"
                    >
                      {member.name}
                    </a>
                  ) : (
                    member.name
                  )}
                </h2>
                <p className="text-gray-600 text-xs leading-relaxed line-clamp-2 min-h-[2.5rem]">
                  {member.role}
                </p>
              </div>
            </div>
          ))}
        </div>

        <footer className="mt-20 pt-8 border-t border-gray-200 text-center text-sm text-gray-500">
          © {new Date().getFullYear()} Medical AI Leaderboard. All rights reserved.
        </footer>
      </div>
    </div>
  );
}
