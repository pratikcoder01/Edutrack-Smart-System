const { supabase, isConfigured } = require('./lib/supabase');

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');

  if (req.method === 'OPTIONS') return res.status(200).end();
  
  if (!isConfigured) {
    return res.status(503).json({ error: 'Supabase environment variables are missing. Please configure them in Vercel.', unconfigured: true });
  }

  try {
    const { data: logs, error } = await supabase
      .from('attendance_logs')
      .select('id, roll, subject, date, status, students(name, class)')
      .order('id', { ascending: false })
      .limit(200);

    if (error) throw error;

    const formattedLogs = logs.map(log => ({
      ...log,
      name: log.students?.name || 'Unknown',
      class: log.students?.class || 'N/A'
    }));

    return res.status(200).json({ logs: formattedLogs });

  } catch (error) {
    console.error('Error fetching all records:', error);
    return res.status(500).json({ error: 'Failed to fetch database records', details: error.message });
  }
};
