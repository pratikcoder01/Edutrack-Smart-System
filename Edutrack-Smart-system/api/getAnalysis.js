const { supabase, isConfigured } = require('./lib/supabase');

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');

  if (req.method === 'OPTIONS') return res.status(200).end();

  if (!isConfigured) {
    return res.status(503).json({ error: 'Database unconfigured', unconfigured: true });
  }

  try {
    // Note: In Supabase Postgres, raw complex aggregations often require RPC functions.
    // For Vercel Serverless limits, pulling the last 1000 logs and aggregating in Node is simple and fast.
    const { data: logs, error } = await supabase
      .from('attendance_logs')
      .select('date, subject, status')
      .eq('status', 'PRESENT')
      .order('id', { ascending: false })
      .limit(1000);

    if (error) throw error;

    // Trend Aggregation
    const trendMap = {};
    const subjectMap = {};
    const statusMap = { PRESENT: 0, ABSENT: 0 }; // Absent require diffing against students table

    logs.forEach(log => {
      trendMap[log.date] = (trendMap[log.date] || 0) + 1;
      subjectMap[log.subject] = (subjectMap[log.subject] || 0) + 1;
      statusMap['PRESENT'] += 1;
    });

    const { count: totalStudents } = await supabase.from('students').select('*', { count: 'exact', head: true });
    // Simplify ABSENT logic for realtime dash assuming total logs / students 
    // Usually we would join but for dashboard visual we take total expected 
    
    // Sort trend dates
    const trendKeys = Object.keys(trendMap).sort().slice(-7);
    const trendLabels = trendKeys.length > 0 ? trendKeys : [new Date().toISOString().split('T')[0]];
    const trendValues = trendKeys.length > 0 ? trendKeys.map(k => trendMap[k]) : [0];

    const subKeys = Object.keys(subjectMap);
    const subLabels = subKeys.length > 0 ? subKeys : ['General'];
    const subValues = subKeys.length > 0 ? subKeys.map(k => subjectMap[k]) : [0];

    return res.status(200).json({
      trend: { labels: trendLabels, values: trendValues },
      subject: { labels: subLabels, values: subValues },
      status: { labels: ['PRESENT', 'ABSENT'], values: [statusMap['PRESENT'], 0] },
      metrics: {
        total_students: totalStudents || 0,
        avg_attendance: totalStudents ? Math.min(100, Math.floor(statusMap['PRESENT']/totalStudents)) : 0,
        peak_date: trendLabels[trendValues.indexOf(Math.max(...trendValues))] || "N/A"
      }
    });

  } catch (error) {
    console.error('Error in getAnalysis:', error);
    return res.status(500).json({ error: 'Analysis failed' });
  }
};
