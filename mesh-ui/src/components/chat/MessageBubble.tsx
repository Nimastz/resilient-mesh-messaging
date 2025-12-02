import React from 'react';
import { format } from 'date-fns';
import { Check, CheckCheck, Clock, AlertCircle, Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function MessageBubble({ message, isMe, onDelete }) {
  const StatusIcon = () => {
    if (!isMe) return null;
    switch (message.status) {
      case 'sending': return <Clock className="w-3 h-3 text-slate-300" />;
      case 'sent': return <CheckCheck className="w-3 h-3 text-slate-400" />;
      case 'delivered': return <CheckCheck className="w-3 h-3 text-green-500" />;
      case 'failed': return <AlertCircle className="w-3 h-3 text-red-300" />;
      default: return <Check className="w-3 h-3 text-slate-300" />;
    }
  };

  return (
    <div className={cn("flex w-full mb-4", isMe ? "justify-end" : "justify-start")}>
       {!isMe && (
          <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-800 mr-2 shrink-0 overflow-hidden mt-auto">
              <img src={message.fromUserAvatar || `https://api.dicebear.com/7.x/avataaars/svg?seed=${message.from}`} className="w-full h-full object-cover" alt="Avatar" />
          </div>
       )}
      <div className={cn(
        "max-w-[80%] md:max-w-[60%] rounded-2xl px-4 py-2 shadow-sm relative group",
        isMe 
          ? "bg-gradient-to-br from-indigo-500 to-violet-600 text-white rounded-tr-sm" 
          : "bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded-tl-sm border border-slate-100 dark:border-slate-700"
      )}>
        <p className="whitespace-pre-wrap break-words text-[15px] leading-relaxed">
          {message.text}
        </p>
        <div className={cn(
          "flex items-center gap-1 text-[10px] mt-1 select-none",
          isMe ? "text-indigo-100 justify-end" : "text-slate-400"
        )}>
          <span>{format(new Date(message.timestamp), 'h:mm a')}</span>
          <StatusIcon />
          {isMe && onDelete && (
            <button 
              onClick={(e) => { e.stopPropagation(); onDelete(); }}
              className="ml-2 opacity-0 group-hover:opacity-100 transition-opacity hover:text-red-200 p-0.5"
              title="Delete message"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}