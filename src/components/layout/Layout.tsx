import { useEffect } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Navbar } from './Navbar'
import { Footer } from './Footer'

function ScrollToTop() {
  const { pathname } = useLocation()

  useEffect(() => {
    if (!window.location.hash) window.scrollTo({ top: 0, behavior: 'auto' })
  }, [pathname])

  return null
}

export function Layout() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <ScrollToTop />
      <a href="#main-content" className="skip-link">
        跳到正文
      </a>
      <Navbar />
      <main id="main-content" tabIndex={-1} className="flex-1 w-full">
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}
