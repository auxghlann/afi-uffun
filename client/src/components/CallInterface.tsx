import { useState, useEffect, useRef } from 'react';
import { PhoneOff, MapPin, Loader2, Play } from 'lucide-react';
import { motion } from 'framer-motion';

interface Message {
  role: 'user' | 'ai' | 'system';
  content: string;
}

interface LocationPayload {
  latitude: number;
  longitude: number;
  accuracy?: number;
}

const CallInterface = () => {
  const [hasLocation, setHasLocation] = useState(false);
  const [locationError, setLocationError] = useState<string | null>(null);
  const [location, setLocation] = useState<LocationPayload | null>(null);
  const [callActive, setCallActive] = useState(false);
  const [callId, setCallId] = useState<string>("");
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [reviewStatus, setReviewStatus] = useState<string | null>(null);
  const statusPollRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (statusPollRef.current) {
        window.clearInterval(statusPollRef.current);
        statusPollRef.current = null;
      }
    };
  }, []);

  // Request GPS Location on mount
  const requestLocation = () => {
    setLocationError(null);
    if (!navigator.geolocation) {
      setLocationError("Geolocation is not supported by your browser.");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocation({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
        });
        setHasLocation(true);
      },
      (error) => {
        setLocationError(`Location access denied. Please allow GPS access to continue. Error: ${error.message}`);
      }
    );
  };

  const simulateLocation = () => {
    // Hardcoded Tuguegarao City coordinates
    setLocation({
      latitude: 17.6134,
      longitude: 121.7269,
      accuracy: 10
    });
    setHasLocation(true);
  };

  const startCall = async () => {
    const newCallId = crypto.randomUUID();
    setCallId(newCallId);
    setCallActive(true);
    // Initial message from AI is usually handled silently or by a system prompt, 
    // but we can trigger an initial greeting if desired.
    setMessages([
      { role: 'ai', content: "Emergency Response Hub. What is your emergency?" }
    ]);
  };

  const endCall = () => {
    setCallActive(false);
    setMessages([]);
    setCallId("");
    setReviewStatus(null);
    if (statusPollRef.current) {
      window.clearInterval(statusPollRef.current);
      statusPollRef.current = null;
    }
  };

  const handleSendMessage = async () => {
    if (!inputText.trim() || !location) return;
    
    const currentInput = inputText;
    const newMessages = [...messages, { role: 'user', content: currentInput } as Message];
    setMessages(newMessages);
    setInputText("");
    setIsProcessing(true);

    try {
      // Send to FastAPI backend
      const res = await fetch("/api/call/message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          call_id: callId,
          message: currentInput,
          location: location
        })
      });

      if (!res.ok) {
        let backendDetail = "Backend request failed";
        try {
          const errData = await res.json();
          backendDetail = errData?.detail || backendDetail;
        } catch {
          // Ignore JSON parse errors and keep fallback detail.
        }
        throw new Error(backendDetail);
      }
      
      const data = await res.json();
      
      const updatedMessages = [...newMessages, { role: 'ai', content: data.response_text } as Message];
      setMessages(updatedMessages);
      
      if (data.review_status) {
        setReviewStatus(data.review_status);
        if (data.review_status === 'pending' && !statusPollRef.current) {
          statusPollRef.current = window.setInterval(async () => {
            const statusRes = await fetch(`/api/call/status?call_id=${callId}`);
            const statusData = await statusRes.json();
            if (statusData.review_status && statusData.review_status !== 'pending') {
              setReviewStatus(statusData.review_status);
              if (statusData.response_text) {
                setMessages(prev => [...prev, { role: 'ai', content: statusData.response_text } as Message]);
              }
              if (statusPollRef.current) {
                window.clearInterval(statusPollRef.current);
                statusPollRef.current = null;
              }
            }
          }, 5000);
        }
      }
      
      if (data.routed_hotlines) {
        console.log("Dispatched Hotlines:", data.routed_hotlines);
        // Optionally update UI to show dispatched units
      }

    } catch (error) {
      console.error("Error communicating with backend", error);
      const reason = error instanceof Error ? error.message : "Connection error";
      setMessages([...newMessages, { role: 'ai', content: `Connection error: ${reason}` }]);
    } finally {
      setIsProcessing(false);
    }
  };

  if (!hasLocation) {
    return (
      <div className="relative flex flex-col items-center justify-center min-h-screen bg-black text-white p-6 overflow-hidden">
        <div className="absolute top-0 left-[-10%] w-[50%] h-[50%] rounded-full bg-primary/20 blur-[150px] pointer-events-none" />
        
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="glass p-8 md:p-12 rounded-[2rem] max-w-md w-full text-center space-y-8 relative z-10"
        >
          <div className="w-20 h-20 bg-primary/10 rounded-full flex items-center justify-center mx-auto text-primary shadow-[0_0_30px_rgba(255,69,0,0.2)]">
            <MapPin size={36} />
          </div>
          <div>
            <h2 className="text-3xl font-bold tracking-tight mb-3">Location Required</h2>
            <p className="text-neutral-400 text-lg">
              To instantly route emergency responders to your area, we require GPS access.
            </p>
          </div>
          
          {locationError && (
            <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-300 text-sm text-left">
              {locationError}
            </div>
          )}

          <div className="space-y-4 pt-4">
            <button 
              onClick={requestLocation}
              className="w-full primary-gradient text-white font-semibold text-lg py-4 rounded-xl shadow-lg shadow-primary/25 hover:shadow-primary/40 transition-all cursor-pointer"
            >
              Allow GPS Location
            </button>
            
            <button 
              onClick={simulateLocation}
              className="w-full glass-panel hover:bg-white/10 text-neutral-200 font-medium text-lg py-4 rounded-xl transition-all cursor-pointer"
            >
              Simulate Location (Demo)
            </button>
          </div>
        </motion.div>
      </div>
    );
  }

  if (!callActive) {
    return (
      <div className="relative flex flex-col items-center justify-center min-h-screen bg-black text-white p-6 overflow-hidden">
        <div className="absolute top-[20%] right-[-10%] w-[60%] h-[60%] rounded-full bg-primary/10 blur-[150px] pointer-events-none" />
        <div className="absolute bottom-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-indigo-500/10 blur-[120px] pointer-events-none" />

        <div className="text-center space-y-12 relative z-10">
          <motion.div 
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="relative mx-auto w-40 h-40 cursor-pointer" 
            onClick={startCall}
          >
            <motion.div 
              animate={{ scale: [1, 1.2, 1], opacity: [0.3, 0.1, 0.3] }}
              transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              className="absolute inset-0 bg-primary rounded-full blur-xl"
            />
            <div className="absolute inset-0 primary-gradient rounded-full flex items-center justify-center shadow-[0_0_50px_rgba(255,69,0,0.4)] border border-white/20">
              <PhoneOff className="text-white transform scale-150 w-10 h-10" />
            </div>
          </motion.div>
          <div>
            <h1 className="text-5xl md:text-6xl font-bold tracking-tight mb-4 text-gradient">Emergency Response</h1>
            <p className="text-neutral-400 text-xl">Tap the button to connect instantly</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen bg-black text-white relative overflow-hidden">
      {/* Dynamic Backgrounds */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-primary/10 blur-[150px] pointer-events-none" />
      <div className="absolute bottom-[10%] right-[-10%] w-[60%] h-[60%] rounded-full bg-indigo-500/5 blur-[150px] pointer-events-none" />

      {/* Top Header */}
      <div className="glass-panel flex justify-between items-center p-6 border-b-0 border-white/5 relative z-10 sticky top-0">
        <div>
          <h2 className="font-bold text-xl tracking-tight">AI Operator</h2>
          <p className="text-green-400 text-sm flex items-center gap-2 font-medium">
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse shadow-[0_0_10px_rgba(74,222,128,0.8)]"></span> Live Connection
          </p>
        </div>
        <div className="flex items-center gap-2 bg-white/10 px-4 py-2 rounded-full text-sm font-medium border border-white/10">
          <MapPin size={14} className="text-primary" /> Location Secured
        </div>
      </div>

      {reviewStatus && (
        <motion.div 
          initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
          className={`px-6 py-4 text-center font-medium shadow-lg z-10 border-b ${
            reviewStatus === 'pending' ? 'bg-yellow-500/20 border-yellow-500/30 text-yellow-300' :
            reviewStatus === 'approved' ? 'bg-green-500/20 border-green-500/30 text-green-300' :
            'bg-red-500/20 border-red-500/30 text-red-300'
          }`}
        >
          {reviewStatus === 'pending' && "Report received. Analyzing with Command Center..."}
          {reviewStatus === 'approved' && "Command center confirmed. Responders dispatched."}
          {reviewStatus === 'rejected' && "Need more details. Please clarify the situation."}
        </motion.div>
      )}

      {/* Main Avatar Area */}
      <div className="flex-1 flex flex-col items-center justify-center relative z-10 p-6 pb-40">
        <div className="relative w-48 h-48 flex items-center justify-center">
          {/* Animated rings */}
          {isProcessing && (
             <>
               <motion.div animate={{ scale: [1, 1.5], opacity: [0.5, 0] }} transition={{ duration: 1.5, repeat: Infinity }} className="absolute inset-0 rounded-full border-2 border-indigo-500/50" />
               <motion.div animate={{ scale: [1, 1.8], opacity: [0.3, 0] }} transition={{ duration: 1.5, repeat: Infinity, delay: 0.2 }} className="absolute inset-0 rounded-full border border-indigo-500/30" />
             </>
          )}
          
          <motion.div 
            animate={{
              scale: isProcessing ? [1, 1.05, 1] : 1,
            }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
            className={`w-32 h-32 rounded-full flex items-center justify-center shadow-2xl relative z-10 border border-white/10
              ${isProcessing ? 'bg-indigo-500/20 shadow-[0_0_40px_rgba(99,102,241,0.4)] backdrop-blur-md' : 'bg-white/5 backdrop-blur-md'}
            `}
          >
            {isProcessing ? (
              <Loader2 className="w-10 h-10 text-indigo-400 animate-spin" />
            ) : (
               <div className="w-4 h-4 rounded-full bg-white/40 shadow-[0_0_15px_rgba(255,255,255,0.5)]" />
            )}
          </motion.div>
        </div>
        
        <div className="mt-12 w-full max-w-2xl text-center">
          {messages.length > 0 ? (
             <motion.div 
               initial={{ opacity: 0, y: 10 }}
               animate={{ opacity: 1, y: 0 }}
               key={messages.length}
               className="text-2xl md:text-3xl font-medium leading-relaxed text-white/90 drop-shadow-md"
             >
               "{messages[messages.length - 1].content}"
             </motion.div>
          ) : (
             <div className="text-xl text-neutral-500 font-medium">Listening for emergency details...</div>
          )}
        </div>
      </div>

      {/* Input & Controls Dock */}
      <div className="fixed bottom-0 left-0 w-full p-4 md:p-6 z-20 pointer-events-none">
        <div className="max-w-2xl mx-auto pointer-events-auto">
          <div className="glass rounded-[2rem] p-2 flex items-center gap-2 shadow-[0_20px_40px_rgba(0,0,0,0.5)]">
            <button 
              onClick={endCall}
              className="w-14 h-14 shrink-0 bg-red-500/20 hover:bg-red-500/40 border border-red-500/30 rounded-full flex items-center justify-center transition-all cursor-pointer"
            >
              <PhoneOff className="w-6 h-6 text-red-400" />
            </button>
            
            <div className="relative flex-1">
              <input 
                type="text" 
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                placeholder="Type emergency..."
                className="w-full bg-transparent border-none py-4 px-4 text-white text-lg focus:outline-none placeholder-neutral-500"
                disabled={isProcessing}
              />
            </div>
            
            <button 
              onClick={handleSendMessage}
              disabled={!inputText.trim() || isProcessing}
              className="w-14 h-14 shrink-0 primary-gradient rounded-full flex items-center justify-center transition-all cursor-pointer shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Play className="w-6 h-6 text-white ml-1" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CallInterface;
