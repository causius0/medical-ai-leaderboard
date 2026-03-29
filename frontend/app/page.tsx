'use client';

import { useState, useEffect, Fragment } from 'react';
import Link from 'next/link';

interface SpecialtyBreakdown {
  [specialty: string]: {
    correct: number;
    total: number;
    accuracy: number;
  };
}

interface SourceBreakdown {
  [source: string]: {
    correct: number;
    total: number;
    accuracy: number;
  };
}

interface Model {
  name: string;
  model_id?: string;
  provider?: string;
  logo?: string;
  total_correct: number;
  total_questions: number;
  accuracy: number;
  specialty_breakdown: SpecialtyBreakdown;
  source_breakdown: SourceBreakdown;
  metadata?: {
    provider?: string;
    cost?: string;
    tokens?: number;
    evaluation_method?: string;
    context_window?: string;
  };
}

interface LeaderboardData {
  models: Model[];
  last_updated: string;
}

export default function Home() {
  const [data, setData] = useState<LeaderboardData | null>(null);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [specialtyFilter, setSpecialtyFilter] = useState<string>('All');
  const [sourceFilter, setSourceFilter] = useState<string>('All');
  const [specialties, setSpecialties] = useState<string[]>([]);
  const [sources, setSources] = useState<string[]>([]);

  useEffect(() => {
    fetch('/leaderboard.json')
      .then((res) => res.json())
      .then((jsonData: LeaderboardData) => {
        setData(jsonData);

        // Extract unique specialties and sources
        const allSpecialties = new Set<string>();
        const allSources = new Set<string>();

        jsonData.models.forEach((model) => {
          Object.keys(model.specialty_breakdown).forEach((specialty) => {
            allSpecialties.add(specialty);
          });
          Object.keys(model.source_breakdown).forEach((source) => {
            allSources.add(source);
          });
        });

        setSpecialties(Array.from(allSpecialties).sort());
        setSources(Array.from(allSources).sort());
      })
      .catch((error) => console.error('Error loading leaderboard data:', error));
  }, []);

  const getAccuracyColor = (accuracy: number) => {
    if (accuracy >= 80) return 'text-green-700';
    if (accuracy >= 60) return 'text-yellow-700';
    return 'text-red-700';
  };

  const getAccuracyBgColor = (accuracy: number) => {
    if (accuracy >= 80) return 'bg-green-100';
    if (accuracy >= 60) return 'bg-yellow-100';
    return 'bg-red-100';
  };

  const getBadgeColor = (rank: number) => {
    if (rank === 1) return 'bg-amber-400';
    if (rank === 2) return 'bg-gray-400';
    if (rank === 3) return 'bg-amber-700';
    return '';
  };

  const toggleRow = (modelName: string) => {
    setExpandedRow(expandedRow === modelName ? null : modelName);
  };

  if (!data) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-900 text-xl">Loading...</div>
      </div>
    );
  }

  // Filter and sort models
  let filteredModels = [...data.models].map((model) => {
    // Create a modified model that displays filtered accuracy
    const displayModel = { ...model };

    if (specialtyFilter !== 'All' && model.specialty_breakdown[specialtyFilter]) {
      // Show specialty-specific accuracy
      const specialtyData = model.specialty_breakdown[specialtyFilter];
      displayModel.accuracy = specialtyData.accuracy;
      displayModel.total_correct = specialtyData.correct;
      displayModel.total_questions = specialtyData.total;
    } else if (sourceFilter !== 'All' && model.source_breakdown[sourceFilter]) {
      // Show source-specific accuracy
      const sourceData = model.source_breakdown[sourceFilter];
      displayModel.accuracy = sourceData.accuracy;
      displayModel.total_correct = sourceData.correct;
      displayModel.total_questions = sourceData.total;
    }

    return displayModel;
  });

  // Filter to only include models that have the selected specialty/source
  if (specialtyFilter !== 'All') {
    filteredModels = filteredModels.filter((model) =>
      model.specialty_breakdown[specialtyFilter]
    );
  }

  if (sourceFilter !== 'All') {
    filteredModels = filteredModels.filter((model) =>
      model.source_breakdown[sourceFilter]
    );
  }

  filteredModels.sort((a, b) => b.accuracy - a.accuracy);

  return (
    <div className="min-h-screen bg-gray-50 p-6 md:p-8">
      <div className="max-w-7xl mx-auto">
        <header className="mb-8 flex justify-between items-start">
          <div>
            <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-2">
              Medical AI Leaderboard
            </h1>
            <p className="text-lg text-gray-600">
              Comparing AI model performance across medical specialties and exam sources
            </p>
          </div>
          <div className="flex gap-4">
            <Link
              href="/project"
              className="px-6 py-2 bg-white border border-gray-200 rounded-full shadow-sm hover:shadow-md transition-all text-gray-700 font-medium"
            >
              About Project
            </Link>
            <Link
              href="/team"
              className="px-6 py-2 bg-white border border-gray-200 rounded-full shadow-sm hover:shadow-md transition-all text-gray-700 font-medium"
            >
              Meet the Team
            </Link>
          </div>
        </header>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="specialty-filter" className="block text-sm font-medium text-gray-700 mb-2">
                Filter by Specialty
              </label>
              <select
                id="specialty-filter"
                value={specialtyFilter}
                onChange={(e) => setSpecialtyFilter(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
              >
                <option value="All">All Specialties</option>
                {specialties.map((specialty) => (
                  <option key={specialty} value={specialty}>
                    {specialty}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="source-filter" className="block text-sm font-medium text-gray-700 mb-2">
                Filter by Source
              </label>
              <select
                id="source-filter"
                value={sourceFilter}
                onChange={(e) => setSourceFilter(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
              >
                <option value="All">All Sources</option>
                {sources.map((source) => (
                  <option key={source} value={source}>
                    {source}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Rank</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Model</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Accuracy</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Score</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredModels.map((model, index) => (
                  <Fragment key={model.name}>
                    <tr
                      key={model.name}
                      className="hover:bg-gray-50 cursor-pointer transition-colors"
                      onClick={() => toggleRow(model.name)}
                    >
                      <td className="px-6 py-4 whitespace-nowrap w-12 text-center">
                        <span className="text-sm font-medium text-gray-500">
                          {index + 1}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-3">
                          {model.logo && (
                            <img
                              src={model.logo}
                              alt={`${model.name} logo`}
                              className="w-8 h-8 object-contain"
                            />
                          )}
                          <div>
                            <div className="text-sm font-semibold text-gray-900">{model.name}</div>
                            {model.provider && (
                              <div className="text-xs text-gray-500">{model.provider}</div>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <span
                            className={`text-sm font-bold ${getAccuracyColor(model.accuracy)}`}
                          >
                            {model.accuracy.toFixed(1)}%
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-600">
                          {model.total_correct} / {model.total_questions}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <button
                          className="text-gray-400 hover:text-gray-600 transition-colors"
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleRow(model.name);
                          }}
                        >
                          {expandedRow === model.name ? (
                            <svg
                              className="w-5 h-5"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M19 9l-7 7-7-7"
                              />
                            </svg>
                          ) : (
                            <svg
                              className="w-5 h-5"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M9 5l7 7-7 7"
                              />
                            </svg>
                          )}
                        </button>
                      </td>
                    </tr>
                    {expandedRow === model.name && (
                      <tr>
                        <td colSpan={5} className="px-6 py-6 bg-gray-50">
                          <div className="space-y-6">
                            <div>
                              <h3 className="text-sm font-semibold text-gray-900 mb-4">
                                Specialty Breakdown
                              </h3>
                              <div className="space-y-3">
                                {Object.entries(model.specialty_breakdown).map(
                                  ([specialty, data]) => (
                                    <div key={specialty}>
                                      <div className="flex justify-between items-center mb-1">
                                        <span className="text-sm text-gray-700">{specialty}</span>
                                        <span className="text-sm font-medium text-gray-900">
                                          {data.accuracy.toFixed(1)}% ({data.correct}/{data.total})
                                        </span>
                                      </div>
                                      <div className="w-full bg-gray-200 rounded-full h-2">
                                        <div
                                          className={`h-2 rounded-full ${getAccuracyBgColor(
                                            data.accuracy
                                          )} transition-all duration-300`}
                                          style={{ width: `${data.accuracy}%` }}
                                        />
                                      </div>
                                    </div>
                                  )
                                )}
                              </div>
                            </div>

                            <div>
                              <h3 className="text-sm font-semibold text-gray-900 mb-4">
                                Source Breakdown
                              </h3>
                              <div className="space-y-3">
                                {Object.entries(model.source_breakdown).map(([source, data]) => (
                                  <div key={source}>
                                    <div className="flex justify-between items-center mb-1">
                                      <span className="text-sm text-gray-700">{source}</span>
                                      <span className="text-sm font-medium text-gray-900">
                                        {data.accuracy.toFixed(1)}% ({data.correct}/{data.total})
                                      </span>
                                    </div>
                                    <div className="w-full bg-gray-200 rounded-full h-2">
                                      <div
                                        className={`h-2 rounded-full ${getAccuracyBgColor(
                                          data.accuracy
                                        )} transition-all duration-300`}
                                        style={{ width: `${data.accuracy}%` }}
                                      />
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="mt-8 text-center text-sm text-gray-500">
          Last updated: {new Date(data.last_updated).toLocaleString()}
        </div>

        <div className="mt-12 md:hidden">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Mobile View</h2>
          <div className="space-y-4">
            {filteredModels.map((model, index) => (
              <div
                key={model.name}
                className="bg-white rounded-lg shadow-sm border border-gray-200 p-4"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    {index < 3 ? (
                      <span
                        className={`inline-flex items-center justify-center w-8 h-8 rounded-full ${getBadgeColor(
                          index + 1
                        )} text-white font-bold text-sm`}
                      >
                        {index + 1}
                      </span>
                    ) : (
                      <span className="text-gray-900 font-medium">{index + 1}</span>
                    )}
                    {model.logo && (
                      <img
                        src={model.logo}
                        alt={`${model.name} logo`}
                        className="w-6 h-6 object-contain"
                      />
                    )}
                    <div className="text-sm font-semibold text-gray-900">{model.name}</div>
                  </div>
                  <div
                    className={`text-lg font-bold ${getAccuracyColor(model.accuracy)}`}
                  >
                    {model.accuracy.toFixed(1)}%
                  </div>
                </div>
                <div className="text-sm text-gray-600 mb-3">
                  {model.total_correct} / {model.total_questions} correct
                </div>
                <button
                  onClick={() => toggleRow(model.name)}
                  className="w-full text-left text-sm text-gray-700 hover:text-gray-900 transition-colors"
                >
                  {expandedRow === model.name ? 'Hide Details' : 'Show Details'}
                </button>
                {expandedRow === model.name && (
                  <div className="mt-4 space-y-4">
                    <div>
                      <h4 className="text-sm font-semibold text-gray-900 mb-2">
                        Specialty Breakdown
                      </h4>
                      <div className="space-y-2">
                        {Object.entries(model.specialty_breakdown).map(
                          ([specialty, data]) => (
                            <div key={specialty}>
                              <div className="flex justify-between items-center mb-1">
                                <span className="text-xs text-gray-700">{specialty}</span>
                                <span className="text-xs font-medium text-gray-900">
                                  {data.accuracy.toFixed(1)}%
                                </span>
                              </div>
                              <div className="w-full bg-gray-200 rounded-full h-1.5">
                                <div
                                  className={`h-1.5 rounded-full ${getAccuracyBgColor(
                                    data.accuracy
                                  )}`}
                                  style={{ width: `${data.accuracy}%` }}
                                />
                              </div>
                            </div>
                          )
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
