import * as React from "react"
import { Bell, Search, User, Settings, LogOut, ChevronDown } from "lucide-react"
import { toast } from "../ui/toast"
import { motion, AnimatePresence } from "framer-motion"

export function TopNav() {
  const [isAvatarOpen, setIsAvatarOpen] = React.useState(false)

  return (
    <header className="h-16 glass-panel border-b-0 border-x-0 rounded-none border-t-0 border-b border-white/10 flex items-center justify-between px-6 relative z-30 shadow-sm">
      <div className="flex items-center gap-4 flex-1">
        <div className="relative group">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-cyan-400 transition-colors" />
          <input 
            type="text" 
            placeholder="Search..." 
            className="h-9 w-64 bg-white/5 border border-white/10 rounded-lg pl-9 pr-12 text-sm text-white placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-cyan-500/50 focus:border-cyan-500/50 transition-all shadow-inner"
          />
          <kbd className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] px-1.5 py-0.5 rounded bg-white/10 font-mono text-muted-foreground pointer-events-none">⌘K</kbd>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <button 
          onClick={() => toast("No new notifications.", "default")}
          className="w-9 h-9 flex items-center justify-center rounded-full text-muted-foreground hover:text-white hover:bg-white/10 transition-colors relative"
        >
          <Bell className="w-5 h-5" />
          <span className="absolute top-2 right-2 w-1.5 h-1.5 bg-cyan-500 rounded-full shadow-[0_0_8px_rgba(6,182,212,0.8)]"></span>
        </button>
        
        <div className="relative">
          <button 
            onClick={() => setIsAvatarOpen(!isAvatarOpen)}
            className="flex items-center gap-2 hover:opacity-80 transition-opacity focus:outline-none"
          >
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-xs font-bold text-white shadow-lg ring-2 ring-white/10">
              OR
            </div>
            <ChevronDown className="w-3 h-3 text-muted-foreground" />
          </button>
          
          <AnimatePresence>
            {isAvatarOpen && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setIsAvatarOpen(false)} />
                <motion.div 
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  transition={{ duration: 0.15 }}
                  className="absolute right-0 top-full mt-2 w-48 glass-panel border border-white/10 shadow-2xl rounded-xl overflow-hidden z-50 py-1"
                >
                  <div className="px-4 py-2 border-b border-white/10 mb-1">
                    <p className="text-sm font-medium text-white">Admin User</p>
                    <p className="text-xs text-muted-foreground">admin@orq.ai</p>
                  </div>
                  <button onClick={() => { toast("Profile: Coming Soon"); setIsAvatarOpen(false) }} className="w-full text-left px-4 py-2 text-sm text-white hover:bg-white/10 transition-colors flex items-center gap-2">
                    <User className="w-4 h-4" /> Profile
                  </button>
                  <button onClick={() => { toast("Settings: Coming Soon"); setIsAvatarOpen(false) }} className="w-full text-left px-4 py-2 text-sm text-white hover:bg-white/10 transition-colors flex items-center gap-2">
                    <Settings className="w-4 h-4" /> Settings
                  </button>
                  <div className="h-px bg-white/10 my-1" />
                  <button disabled className="w-full text-left px-4 py-2 text-sm text-muted-foreground flex items-center gap-2 opacity-50 cursor-not-allowed">
                    <LogOut className="w-4 h-4" /> Logout
                  </button>
                </motion.div>
              </>
            )}
          </AnimatePresence>
        </div>
      </div>
    </header>
  )
}
