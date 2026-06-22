import { Link, useLocation } from 'react-router-dom'
import { Moon, Sun, Menu } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { useTheme } from '@/hooks/useTheme'
import { cn } from '@/lib/utils'
import { siteContainerClass } from './constants'

const navItems = [
  { href: '/blog', label: '博客' },
  { href: '/projects', label: '作品集' },
  { href: '/resources', label: '资源导航' },
  { href: '/ai-daily', label: 'AI日报' },
  { href: '/about', label: '关于' },
] as const

export function Navbar() {
  const { resolvedTheme, toggleTheme, mounted } = useTheme()
  const location = useLocation()

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className={cn(siteContainerClass, 'flex h-16 items-center gap-6')}>
        <Button
          variant="link"
          className="flex items-center gap-2.5 font-bold text-lg p-0 shrink-0"
          render={<Link to="/" />}
        >
          <Avatar className="h-8 w-8">
            <AvatarImage src="/avatar.jpg" alt="icemouce" />
            <AvatarFallback className="text-xs">IM</AvatarFallback>
          </Avatar>
          icemouce
        </Button>

        <nav className="hidden md:flex flex-1 items-center justify-center gap-1">
          {navItems.map((item) => (
            <Button
              key={item.href}
              variant="ghost"
              className={cn(
                'text-sm',
                location.pathname.startsWith(item.href) && 'bg-accent text-accent-foreground'
              )}
              render={<Link to={item.href} />}
            >
              {item.label}
            </Button>
          ))}
        </nav>

        <div className="flex items-center gap-1 md:ml-auto">
          {mounted && (
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleTheme}
              className="hidden md:inline-flex"
              aria-label="切换主题"
            >
              {resolvedTheme === 'dark' ? (
                <Sun className="h-4 w-4" />
              ) : (
                <Moon className="h-4 w-4" />
              )}
            </Button>
          )}

          <Sheet>
            <SheetTrigger
              className="md:hidden"
              render={<Button variant="ghost" size="icon" aria-label="打开菜单" />}
            >
              <Menu className="h-4 w-4" />
            </SheetTrigger>
            <SheetContent side="right">
              <nav className="flex flex-col gap-2 pt-6">
                {navItems.map((item) => (
                  <Button
                    key={item.href}
                    variant="ghost"
                    className={cn(
                      'justify-start text-base',
                      location.pathname.startsWith(item.href) && 'bg-accent text-accent-foreground'
                    )}
                    render={<Link to={item.href} />}
                  >
                    {item.label}
                  </Button>
                ))}
                {mounted && (
                  <Button
                    variant="ghost"
                    className="justify-start text-base"
                    onClick={toggleTheme}
                  >
                    {resolvedTheme === 'dark' ? (
                      <>
                        <Sun className="h-4 w-4 mr-2" /> 切换亮色模式
                      </>
                    ) : (
                      <>
                        <Moon className="h-4 w-4 mr-2" /> 切换暗色模式
                      </>
                    )}
                  </Button>
                )}
              </nav>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  )
}
