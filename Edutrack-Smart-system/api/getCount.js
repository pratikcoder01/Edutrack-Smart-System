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

    // Get total students
    const { count: totalStudents, error: studentErr } = await supabase
      .from('students')
      .select('*', { count: 'exact', head: true });

    if (studentErr) throw studentErr;

    // Get present students today
    const { count: presentCount, error: logErr } = await supabase
      .from('attendance_logs')
      .select('*', { count: 'exact', head: true })
      .eq('date', today)
      .eq('status', 'PRESENT');

    if (logErr) throw logErr;

    const present = presentCount || 0;
    const total = totalStudents || 0;
    const absent = Math.max(0, total - present);
    const percentage = total > 0 ? Math.floor((present / total) * 100) : 0;

    return res.status(200).json({
      present,
      absent,
      percentage,
      active: true // Active could be made dynamic later
    });

  } catch (error) {
    console.error('Error fetching count:', error);
    return res.status(500).json({ error: error.message });
  }
};
