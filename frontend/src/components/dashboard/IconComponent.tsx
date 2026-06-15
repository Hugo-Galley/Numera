import { 
  Tag, Coffee, ShoppingBag, Utensils, Car, Home, Heart, Zap, Music, Smartphone, Plane, Gift, 
  Briefcase, CreditCard, Wallet, Banknote, Trophy, Activity, User, Film, Dumbbell,
  Airplay, AlarmClock, Archive, Award, Backpack, Bath, Beer, Bell, Bike, Book, Box, Camera,
  Clapperboard, Cloud, Compass, Cookie, Cpu, Dice5, Dog, Droplet, Egg, Eye, Fan, Feather,
  Fish, Flag, Flashlight, FlaskConical, Flower, Footprints, Fuel, Gamepad2, GlassWater,
  Globe, Grape, Hammer, IceCream, Key, Laptop, Library, Lightbulb, Locate, Lock,
  Map, Mic, Monitor, Moon, Mountain, Mouse, Network, Newspaper, Nut, Package, Paintbrush,
  Palmtree, Paperclip, PawPrint, Phone, Pizza, Plug, Printer, Puzzle, Radio, Receipt,
  Recycle, Rocket, Route, Rss, Sailboat, Scissors, ScreenShare, Search, Settings as SettingsIcon,
  Shield, Ship, Shirt, ShowerHead, Skull, Smile, Snowflake, Speaker, Sprout, Stamp, Star,
  Stethoscope, Sun, Sunrise, Sunset, Tablet, Target, Tent, Terminal, Thermometer, Ticket,
  Timer, Train, Trash, TreeDeciduous, TreePine, Trees, Tv, Umbrella, UtilityPole, Variable,
  Video, Voicemail, Volume2, Watch, Waves, Webcam, Weight, Wifi, Wind, Wine, Wrench
} from "lucide-react"

const ICON_MAP: Record<string, any> = {
  Coffee, ShoppingBag, Utensils, Car, Home, Heart, Zap, Music, Smartphone, Plane, Gift, 
  Briefcase, CreditCard, Wallet, Banknote, 
  Trophy, Activity, User, Film, Dumbbell, Tag,
  Airplay, AlarmClock, Archive, Award, Backpack, Bath, Beer, Bell, Bike, Book, Box, Camera,
  Clapperboard, Cloud, Compass, Cookie, Cpu, Dice5, Dog, Droplet, Egg, Eye, Fan, Feather,
  Fish, Flag, Flashlight, FlaskConical, Flower, Footprints, Fuel, Gamepad2, GlassWater,
  Globe, Grape, Hammer, IceCream, Key, Laptop, Library, Lightbulb, Locate, Lock,
  Map, Mic, Monitor, Moon, Mountain, Mouse, Network, Newspaper, Nut, Package, Paintbrush,
  Palmtree, Paperclip, PawPrint, Phone, Pizza, Plug, Printer, Puzzle, Radio, Receipt,
  Recycle, Rocket, Route, Rss, Sailboat, Scissors, ScreenShare, Search, Settings: SettingsIcon,
  Shield, Ship, Shirt, ShowerHead, Skull, Smile, Snowflake, Speaker, Sprout, Stamp, Star,
  Stethoscope, Sun, Sunrise, Sunset, Tablet, Target, Tent, Terminal, Thermometer, Ticket,
  Timer, Train, Trash, TreeDeciduous, TreePine, Trees, Tv, Umbrella, UtilityPole, Variable,
  Video, Voicemail, Volume2, Watch, Waves, Webcam, Weight, Wifi, Wind, Wine, Wrench
}

export const IconComponent = ({ name, className }: { name?: string | null, className?: string }) => {
  if (!name) return <Tag className={className} />
  if (name && (name.startsWith("M") || name.startsWith("<svg") || name.includes("<path"))) {
    return (
      <svg 
        viewBox="0 0 24 24" 
        className={className} 
        fill="none" 
        stroke="currentColor" 
        strokeWidth="2" 
        strokeLinecap="round" 
        strokeLinejoin="round"
      >
        {name.startsWith("<svg") ? (
          <g dangerouslySetInnerHTML={{ __html: name.replace(/<svg[^>]*>|<\/svg>/g, '') }} />
        ) : name.includes("<path") ? (
          <g dangerouslySetInnerHTML={{ __html: name }} />
        ) : (
          <path d={name} />
        )}
      </svg>
    )
  }
  const Icon = ICON_MAP[name || "Tag"] || Tag
  return <Icon className={className} />
}
