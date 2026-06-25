import { usePatient } from './context/PatientContext'
import LoginScreen from './components/LoginScreen'
import ChatScreen from './components/ChatScreen'

export default function App() {
  const { patientId } = usePatient()

  return patientId ? <ChatScreen /> : <LoginScreen />
}
