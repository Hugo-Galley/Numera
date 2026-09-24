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
  ArrowRightLeft,
  Timer, Train, Trash, TreeDeciduous, TreePine, Trees, Tv, Umbrella, UtilityPole, Variable,
  Video, Voicemail, Volume2, Watch, Waves, Webcam, Weight, Wifi, Wind, Wine, Wrench
} from "lucide-react"

export const ICON_MAP: Record<string, any> = {
  Coffee, ShoppingBag, Utensils, Car, Home, Heart, Zap, Music, Smartphone, Plane, Gift, 
  Briefcase, CreditCard, Wallet, Banknote, ArrowRightLeft,
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

const SVG_PATH_REGEX = /^[\s\dMmZzLlHhVvCcSsQqTtAa,.-]+$/

export const IconComponent = ({ name, className }: { name?: string | null, className?: string }) => {
  if (!name) return <Tag className={className} />

  // If name is a raw SVG path (starting with M and only containing valid path characters)
  if (name.startsWith("M") && SVG_PATH_REGEX.test(name)) {
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
        <path d={name} />
      </svg>
    )
  }

  // If name is an SVG snippet containing <path ... d="..." />, safely extract d attributes without innerHTML
  if (name.includes("<path")) {
    const matches = [...name.matchAll(/d=["']([^"']+)["']/gi)]
    if (matches.length > 0) {
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
          {matches.map((m, idx) => (
            <path key={idx} d={m[1]} />
          ))}
        </svg>
      )
    }
  }

  const Icon = ICON_MAP[name] || Tag
  return <Icon className={className} />
}
