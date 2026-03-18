const { supabase, isConfigured } = require('./lib/supabase');

module.exports = async (req, res) => {
  // Set CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }
  
  if (!isConfigured) {
    return res.status(503).json({ error: 'Database unconfigured', unconfigured: true });
  }

  try {
    const today = new Date().toISOString().split('T')[0];

    // Fetch the students with their attendance status
    const { data: logs, error } = await supabase
      .from('attendance_logs')
      .select('id, roll, subject, date, status, students(name, class)')
      .eq('date', today)
      .order('id', { ascending: false })
      .limit(50); // Get latest 50 logs

    if (error) throw error;

    // Transform relation output
    const formattedLogs = logs.map(log => ({
      ...log,
      name: log.students?.name || 'Unknown',
      class: log.students?.class || 'N/A'
    }));

    return res.status(200).json({ logs: formattedLogs });

  } catch (error) {
    console.error('Error fetching attendance logs:', error);
    return res.status(500).json({ error: error.message });
  }
};
