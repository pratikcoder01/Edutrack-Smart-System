const { createClient } = require('@supabase/supabase-js');

// Graceful fallback for unconfigured environments
const supabaseUrl = process.env.SUPABASE_URL || '';
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || '';

// Initialize client if keys exist, otherwise return a dummy client that throws clean errors
const supabase = (supabaseUrl && supabaseKey) 
  ? createClient(supabaseUrl, supabaseKey) 
  : null;

module.exports = {
  supabase,
  isConfigured: !!supabase
};
