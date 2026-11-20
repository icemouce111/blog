import { useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { Moon, Sun, Menu } from 'lucide-react'
import { Button, buttonVariants } from '@/components/ui/button'
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { useTheme } from '@/hooks/useTheme'
import { cn } from '@/lib/utils'
import { siteContainerClass } from './constants'

const navItems = [
  { href: '/blog', label: '博客' },
  { href: '/projects', label: '作品集' },
  { href: '/resources', label: '资源导航' },
  { href: '/tools', label: '工具集' },
  { href: '/ai-daily', label: 'AI 情报' },
  { href: '/about', label: '关于' },
] as const

export function Navbar() {
  const { resolvedTheme, toggleTheme, mounted } = useTheme()
  const [menuOpen, setMenuOpen] = useState(false)
  const links = (mobile = false) =>
    navItems.map((item) => (
      <NavLink
        key={item.href}
        to={item.href}
        onClick={() => setMenuOpen(false)}
        className={({ isActive }) =>
          cn(
            buttonVariants({ variant: 'ghost' }),
            mobile && 'justify-start text-base',
            isActive && 'bg-accent text-accent-foreground',
          )
        }
      >
        {item.label}
      </NavLink>
    ))
  return (
    <header className="site-navbar sticky top-0 z-50 w-full border-b">
      <div className={cn(siteContainerClass, 'site-navbar-inner flex items-center gap-6')}>
        <Link to="/" className="site-brand flex items-center gap-2.5 font-bold text-lg shrink-0">
          <Avatar className="h-8 w-8">
            <AvatarImage src="/avatar.jpg" alt="" />
            <AvatarFallback>IM</AvatarFallback>
          </Avatar>
          icemouce
        </Link>
        <nav
          aria-label="主导航"
          className="hidden lg:flex flex-1 items-center justify-center gap-1"
        >
          {links()}
        </nav>
        <div className="flex items-center gap-1 ml-auto">
          {mounted && (
            <Button variant="ghost" size="icon" onClick={toggleTheme} aria-label="切换主题">
              {resolvedTheme === 'dark' ? <Sun /> : <Moon />}
            </Button>
          )}
          <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
            <SheetTrigger
              className="lg:hidden"
              render={<Button variant="ghost" size="icon" aria-label="打开菜单" />}
            >
              <Menu />
            </SheetTrigger>
            <SheetContent side="right" className="site-menu-sheet" aria-describedby={undefined}>
              <SheetTitle>浏览本站</SheetTitle>
              <nav aria-label="手机主导航" className="flex flex-col gap-2 pt-6">
                {links(true)}
              </nav>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  )
}
