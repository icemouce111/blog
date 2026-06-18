import { Link, useLocation } from 'react-router-dom'
import { Moon, Sun, Menu } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'
import { useTheme } from '@/hooks/useTheme'
import { cn } from '@/lib/utils'

const navItems = [
  { href: '/blog', label: '博客' },
  { href: '/projects', label: '作品集' },
  { href: '/resources', label: '资源导航' },
  { href: '/about', label: '关于' },
] as const

export function Navbar() {
  const { resolvedTheme, toggleTheme, mounted } = useTheme()
  const location = useLocation()

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto flex h-14 items-center px-4 max-w-5xl">
        <Button
          variant="link"
          className="font-bold text-lg mr-6 p-0"
          render={<Link to="/" />}
        >
          icemouce
        </Button>

        <nav className="hidden md:flex items-center gap-1">
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

        <div className="flex-1" />

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
            render={<Button variant="ghost" size="icon" />}
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
    </header>
  )
}
