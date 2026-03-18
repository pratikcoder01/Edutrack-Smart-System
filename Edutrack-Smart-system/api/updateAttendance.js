const { supabase, isConfigured } = require('./lib/supabase');

module.exports = async (req, res) => {
  // Set CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (!isConfigured) {
    return res.status(503).json({ error: 'Database unconfigured', unconfigured: true });
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { roll, subject = 'General', confidence = 100 } = req.body;
    
    if (!roll) {
      return res.status(400).json({ error: 'Roll number is required' });
    }

    const today = new Date().toISOString().split('T')[0];
    
    // Check if already present today
    const { data: existing, error: checkErr } = await supabase
      .from('attendance_logs')
      .select('id')
      .eq('roll', roll)
      .eq('date', today)
      .eq('subject', subject)
      .limit(1);
      
    if (checkErr) throw checkErr;
    
    if (existing && existing.length > 0) {
      return res.status(200).json({ message: 'Already marked present today', roll });
    }

    // Insert new attendance log
    const { data: insert, error: insertErr } = await supabase
      .from('attendance_logs')
      .insert([
        { roll, subject, date: today, status: 'PRESENT' }
      ]);
      
    if (insertErr) throw insertErr;

    // Trigger realtime UI updates using Supabase Broadcaster (or rely on UI polling count)
    return res.status(200).json({ message: 'Attendance updated successfully', roll });

  } catch (error) {
    console.error('Error updating attendance:', error);
    return res.status(500).json({ error: error.message });
  }
};
